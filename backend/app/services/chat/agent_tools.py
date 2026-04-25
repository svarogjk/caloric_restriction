"""
PydanticAI Agent Tools for the GEO Survival Analysis chat system.

Tools use RunContext[AgentDeps] for dependency injection — no closures needed.
Services are accessed via ctx.deps at runtime, injected at startup.
"""

import json
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai import RunContext

if TYPE_CHECKING:
    from app.services.chat.dataset_rag_service import DatasetRAGService
    from app.services.chat.estimation_service import QueryEstimationService
    from app.services.chat.geo_preview_service import GEOPreviewService

logger = logging.getLogger(__name__)


@dataclass
class AgentDeps:
    """Dependency container injected into all agent tools at run time."""

    rag_service: "DatasetRAGService"
    estimation_service: "QueryEstimationService"
    geo_preview_service: "GEOPreviewService"


async def search_known_datasets(ctx: RunContext["AgentDeps"], query: str) -> str:
    """
    Search the indexed GEO dataset catalogue using semantic similarity.

    Use this to answer questions like "do we have any bladder cancer datasets?"
    or "which datasets have the most samples?" before recommending queries.

    Args:
        query: Natural-language description of the datasets to find

    Returns:
        Summary of the most relevant indexed datasets
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
            genes = meta.get("n_genes", "?")
            lines.append(f"- {acc}: {samples} samples, {genes} genes")
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
        result = await ctx.deps.estimation_service.estimate_query(query)
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
    organism: str = "Homo sapiens",
) -> str:
    """
    Perform a live search of NCBI GEO to preview available datasets.

    Use this to show the user what GEO has available for their topic before
    committing to a full analysis run.

    Args:
        query: Search keywords (e.g. "breast cancer survival microarray")
        organism: Organism filter (default: Homo sapiens)

    Returns:
        Summary of matching GEO datasets with survival keyword counts
    """
    try:
        preview = await ctx.deps.geo_preview_service.get_preview(
            query=query, organism=organism, max_preview=8
        )
        preview_dict = ctx.deps.geo_preview_service.preview_to_dict(preview)
        total = preview_dict.get("total_datasets", 0)
        survival = preview_dict.get("datasets_with_survival_keywords", 0)
        result = (
            f"Found {total} GEO datasets for '{query}'\n"
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

    url = (
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        f"?db=gene&term={gene_symbol}[sym]+AND+Homo+sapiens[organism]"
        "&retmode=json&retmax=1"
    )
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            search_resp = await client.get(url)
            search_resp.raise_for_status()
            ids = search_resp.json().get("esearchresult", {}).get("idlist", [])
            if not ids:
                return f"No NCBI Gene entry found for '{gene_symbol}'."

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


# Active tool list — run_survival_analysis intentionally excluded (user triggers via UI)
AGENT_TOOLS = [search_known_datasets, estimate_query, search_geo_datasets, get_gene_info]
