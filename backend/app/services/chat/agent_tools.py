"""
PydanticAI Agent Tools for the GEO Survival Analysis chat system.

Tools use RunContext[AgentDeps] for dependency injection — no closures needed.
Services are accessed via ctx.deps at runtime, injected at startup.
"""

import json
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from pydantic_ai import RunContext

if TYPE_CHECKING:
    from app.services.chat.dataset_rag_service import DatasetRAGService
    from app.services.chat.estimation_service import QueryEstimationService
    from app.services.chat.geo_preview_service import GEOPreviewService
    from app.services.signature_service import SignatureService

logger = logging.getLogger(__name__)


@dataclass
class AgentDeps:
    """Dependency container injected into all agent tools at run time."""

    rag_service: "DatasetRAGService"
    estimation_service: "QueryEstimationService"
    geo_preview_service: "GEOPreviewService"
    user_settings: dict | None = None  # per-request user configuration
    user_id: str | None = None         # authenticated user ID (None for guests)
    db_session: Any | None = None      # per-request DB session for history queries
    model: str = "mistral-large"       # active LLM selection, forwarded to sub-services
    # Clinical console (agent-orchestrated patient workflow):
    patient_context: dict | None = None
    # Session state that is NOT about a patient: settings, whether an analysis is
    # running, what the last one produced. Kept separate from patient_context so
    # that model's privacy contract stays exactly what it says it is.
    research_context: dict | None = None    # de-identified chart snapshot (PatientContext.model_dump())
    signature_service: "SignatureService | None" = None  # for model lookups/evidence
    action_sink: list | None = None    # console_actions.py tools append intents here;
                                        # the browser re-validates and executes each one —
                                        # the agent never touches patient data directly.


async def search_known_datasets(ctx: RunContext["AgentDeps"], query: str) -> str:
    """
    Search the indexed GEO dataset catalogue using semantic similarity.

    Use this to answer questions like "do we have any bladder cancer datasets?"
    or "which datasets have the most samples?" before recommending queries.

    Args:
        query: Natural-language description of the datasets to find

    Returns:
        Summary of the most relevant indexed datasets with GSE accession IDs
    """
    try:
        docs = await ctx.deps.rag_service.search(query, k=5)
        if not docs:
            return "No matching datasets found in the local index."
        lines = []
        for doc in docs:
            meta = doc.get("metadata") or {}
            acc = meta.get("accession", doc.get("accession", "unknown"))
            samples = meta.get("n_samples", "?")
            title = meta.get("title", "")[:60]
            organism = meta.get("organism", "")
            parts = [f"- {acc}: {samples} samples"]
            if organism:
                parts.append(f"organism={organism}")
            if title:
                parts.append(f'"{title}"')
            lines.append(" | ".join(parts))
        return "\n".join(lines)
    except Exception as exc:
        logger.warning(f"search_known_datasets failed: {exc}")
        return f"Dataset search unavailable: {exc}"


async def estimate_query(ctx: RunContext["AgentDeps"], query: str) -> str:
    """
    Estimate how likely a survival analysis query is to find good GEO data.

    Use this before suggesting the user run a full analysis, to check confidence
    and surface query improvement suggestions.

    Args:
        query: The proposed survival analysis search query

    Returns:
        Confidence score, estimated dataset count, and improvement suggestions
    """
    try:
        result = await ctx.deps.estimation_service.estimate_query(query, model=ctx.deps.model)
        parts = [
            f"Confidence: {result.confidence_score:.0%}",
            f"Estimated datasets: {result.estimated_datasets}",
            f"Estimated time: {result.estimated_time_seconds:.0f}s",
            f"Can proceed: {result.can_proceed}",
        ]
        if result.suggestions:
            parts.append("Suggestions: " + "; ".join(result.suggestions[:3]))
        if result.improved_query:
            parts.append(f"Improved query: {result.improved_query}")
        return "\n".join(parts)
    except Exception as exc:
        logger.warning(f"estimate_query tool failed: {exc}")
        return f"Estimation unavailable: {exc}"


async def search_geo_datasets(
    ctx: RunContext["AgentDeps"],
    query: str,
    organism: str | None = None,
) -> str:
    """
    Perform a live search of NCBI GEO to preview available datasets.

    Use this to show the user what GEO has available for their topic before
    committing to a full analysis run.

    Args:
        query: Search keywords (e.g. "breast cancer survival microarray")
        organism: Organism filter; if omitted, uses the user's configured organism

    Returns:
        Summary of matching GEO datasets with GSE accession IDs and survival keyword counts
    """
    # Resolve organism: explicit arg > user setting > default
    effective_organism = (
        organism
        or (ctx.deps.user_settings or {}).get("organism")
        or "Homo sapiens"
    )
    try:
        preview = await ctx.deps.geo_preview_service.get_preview(
            query=query, organism=effective_organism, max_preview=8
        )
        preview_dict = ctx.deps.geo_preview_service.preview_to_dict(preview)
        total = preview_dict.get("total_datasets", 0)
        survival = preview_dict.get("datasets_with_survival_keywords", 0)
        result = (
            f"Found {total} GEO datasets for '{query}' (organism: {effective_organism})\n"
            f"  - {survival} include survival/outcome keywords\n"
        )
        top = preview_dict.get("top_datasets", [])[:3]
        for ds in top:
            result += f"  - {ds.get('accession', '?')}: {ds.get('title', '')[:80]}\n"
        warnings = preview_dict.get("warnings", [])
        for w in warnings[:2]:
            result += f"  ⚠ {w}\n"
        return result.strip()
    except Exception as exc:
        logger.warning(f"search_geo_datasets tool failed: {exc}")
        return f"GEO preview unavailable: {exc}"


async def get_gene_info(ctx: RunContext["AgentDeps"], gene_symbol: str) -> str:
    """
    Retrieve basic information about a gene from NCBI Entrez.

    Use this when the user asks about a specific gene's function or role.

    Args:
        gene_symbol: Official gene symbol (e.g. "BRCA1", "TP53")

    Returns:
        Gene summary including function and associated diseases
    """
    import httpx

    # Use user's organism setting if available
    organism = (ctx.deps.user_settings or {}).get("organism") or "Homo sapiens"
    organism_ncbi = organism.replace(" ", "+")
    url = (
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        f"?db=gene&term={gene_symbol}[sym]+AND+{organism_ncbi}[organism]"
        "&retmode=json&retmax=1"
    )
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            search_resp = await client.get(url)
            search_resp.raise_for_status()
            ids = search_resp.json().get("esearchresult", {}).get("idlist", [])
            if not ids:
                return f"No NCBI Gene entry found for '{gene_symbol}' in {organism}."

            summary_url = (
                "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
                f"?db=gene&id={ids[0]}&retmode=json"
            )
            sum_resp = await client.get(summary_url)
            sum_resp.raise_for_status()
            data = sum_resp.json().get("result", {}).get(ids[0], {})
            name = data.get("name", gene_symbol)
            description = data.get("description", "")
            summary = data.get("summary", "No summary available.")
            return f"{name} ({gene_symbol}): {description}\n{summary[:500]}"
    except (httpx.HTTPStatusError, httpx.RequestError, KeyError, json.JSONDecodeError) as exc:
        logger.warning(f"get_gene_info failed for {gene_symbol}: {exc}")
        return f"Gene info unavailable: {exc}"


async def get_user_recent_results(
    ctx: RunContext["AgentDeps"],
    limit: int = 5,
) -> str:
    """
    Retrieve the user's recent survival analysis results from their history.

    Use this when the user asks about their previous analyses, wants to compare
    to past results, or asks "what have I analyzed before?".

    Returns:
        Summary of recent analyses with query, top genes, and dataset counts
    """
    if not ctx.deps.user_id or not ctx.deps.db_session:
        return "No analysis history available — you need to be logged in to access your history."

    try:
        from sqlalchemy import select
        from app.models.database import AnalysisResult

        stmt = (
            select(AnalysisResult)
            .where(AnalysisResult.user_id == ctx.deps.user_id)
            .order_by(AnalysisResult.created_at.desc())
            .limit(limit)
        )
        result = await ctx.deps.db_session.execute(stmt)
        records = result.scalars().all()

        if not records:
            return "No previous analyses found in your history."

        lines = []
        for r in records:
            result_data = r.result_data or {}
            common_genes = result_data.get("common_genes", [])
            top_genes = [g.get("gene_symbol", "?") for g in common_genes[:3] if g.get("gene_symbol")]
            date_str = r.created_at.strftime("%Y-%m-%d") if r.created_at else "?"
            lines.append(
                f"- [{date_str}] '{r.query}' | "
                f"Datasets: {r.n_datasets_analyzed} | "
                f"Top genes: {', '.join(top_genes) if top_genes else 'none'}"
            )
        return "\n".join(lines)
    except Exception as exc:
        logger.warning(f"get_user_recent_results failed: {exc}")
        return f"Could not retrieve analysis history: {exc}"


async def get_signature_model_evidence(ctx: RunContext["AgentDeps"], model_id: str) -> str:
    """
    Retrieve the real cohort provenance of a prognostic risk model: which GEO
    series it was trained and validated on, per-cohort sample/event counts and
    C-index, pooled discrimination, gene count, and whether it is a synthetic
    demo model.

    Call this whenever the clinician asks what a risk score is based on, how
    trustworthy it is, or which datasets support it — this is the commonest
    question about a patient's risk model and the answer must cite real GSE
    accessions, not a restatement of the score itself.

    Args:
        model_id: The prognostic model id from the active patient chart

    Returns:
        Training/validation cohort accessions with sample counts and C-index,
        or a plain-language message if the model can't be found
    """
    try:
        service = ctx.deps.signature_service
        if service is None:
            return "Model evidence lookup unavailable — signature service not configured."
        model = service.get_model(model_id)
        if model is None:
            return f"No model found with id '{model_id}'."

        lines = [
            f"Model {model.model_id} ({model.cancer_type or 'unspecified cancer type'})"
            f"{' — SYNTHETIC DEMO MODEL, not fitted on real cohorts' if model.is_demo else ''}",
            f"Trained on {model.training_accession} (n={model.n_training_samples})",
            f"Signature: {len(model.genes)} genes, pooled C-index {model.pooled_c_index:.3f}",
        ]
        if model.cohort_validations:
            lines.append("Cohort validations:")
            for cv in model.cohort_validations:
                lines.append(
                    f"  - {cv.accession} ({cv.role}): n={cv.n_samples}, "
                    f"events={cv.n_events}, C-index={cv.c_index:.3f}"
                )
        if model.c_index_combined is not None:
            lines.append(
                f"Combined (expression + clinical) C-index: {model.c_index_combined:.3f}"
                + (f" (Δ {model.delta_c_index:+.3f} over expression alone)" if model.delta_c_index is not None else "")
            )
        return "\n".join(lines)
    except (AttributeError, KeyError, ValueError) as exc:
        logger.warning(f"get_signature_model_evidence failed for {model_id}: {exc}")
        return f"Model evidence unavailable: {exc}"


# Active READ tools. Running an analysis is a console ACTION tool
# (run_survival_analysis in console_actions.py): it proposes the run and the
# browser executes it, so a 2-5 minute job never blocks an agent turn.
# These are READ tools: they query real data and count toward the Domain Score.
# Console workflow ACTION tools live in console_actions.py and are excluded from
# scoring (see ACTION_TOOL_NAMES in pydantic_ai_service.py) — they orchestrate
# the UI, they don't ground anything.
AGENT_TOOLS = [
    search_known_datasets,
    estimate_query,
    search_geo_datasets,
    get_gene_info,
    get_user_recent_results,
    get_signature_model_evidence,
]
