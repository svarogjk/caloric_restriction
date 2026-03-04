"""
LangChain Agent Tools for the GEO Survival Analysis chat system.

Each @tool is an async function wrapping an existing service.
The module exposes `build_tools(...)` which returns a ready list of tools
with service instances bound via closures — no global state.
"""

import json
import logging
from typing import TYPE_CHECKING

from langchain_core.tools import tool

if TYPE_CHECKING:
    from app.services.chat.dataset_rag_service import DatasetRAGService
    from app.services.chat.estimation_service import QueryEstimationService
    from app.services.chat.geo_preview_service import GEOPreviewService
    from app.services.geo_survival_workflow_orchestrator import (
        GEOSurvivalWorkflowOrchestrator,
    )

logger = logging.getLogger(__name__)


def build_tools(
    rag_service: "DatasetRAGService",
    estimation_service: "QueryEstimationService",
    geo_preview_service: "GEOPreviewService",
    orchestrator: "GEOSurvivalWorkflowOrchestrator",
) -> list:
    """
    Build and return all agent tools with services bound via closures.

    Args:
        rag_service: pgvector RAG service for dataset metadata search
        estimation_service: Query estimation service
        geo_preview_service: GEO live preview service
        orchestrator: Full survival analysis workflow orchestrator

    Returns:
        List of LangChain tools ready to pass to AgentExecutor
    """

    @tool
    async def search_known_datasets(query: str) -> str:
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
            docs = await rag_service.search(query, k=5)
            if not docs:
                return "No matching datasets found in the local index."
            lines = []
            for doc in docs:
                meta = doc.metadata
                acc = meta.get("accession", "unknown")
                samples = meta.get("n_samples", "?")
                genes = meta.get("n_genes", "?")
                lines.append(f"- {acc}: {samples} samples, {genes} genes")
            return "\n".join(lines)
        except Exception as exc:
            logger.warning(f"search_known_datasets failed: {exc}")
            return f"Dataset search unavailable: {exc}"

    @tool
    async def estimate_query(query: str) -> str:
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
            result = await estimation_service.estimate_query(query)
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

    @tool
    async def search_geo_datasets(query: str, organism: str = "Homo sapiens") -> str:
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
            preview = await geo_preview_service.get_preview(
                query=query, organism=organism, max_preview=8
            )
            preview_dict = geo_preview_service.preview_to_dict(preview)
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

    @tool
    async def run_survival_analysis(
        query: str,
        max_datasets: int = 5,
        organism: str | None = None,
    ) -> str:
        """
        Run a full survival analysis pipeline on GEO datasets matching the query.

        This is an expensive operation (minutes). Only trigger when the user
        explicitly asks to run or start an analysis, and when estimate_query
        confirms confidence >= 0.4.

        Args:
            query: Survival analysis search query (e.g. "breast cancer overall survival")
            max_datasets: Maximum datasets to analyse (default 5 for speed)
            organism: Optional organism filter (e.g. "Homo sapiens")

        Returns:
            Summary of top genes associated with survival outcomes
        """
        try:
            result = await orchestrator.analyze_query(
                query=query,
                max_datasets=max_datasets,
                organism=organism,
                cancer_genes_only=False,
            )
            if not result or not result.common_survival_genes:
                return "Analysis completed but no significant survival genes were found."

            lines = [
                f"Survival analysis complete across {result.n_datasets_analyzed} datasets "
                f"({result.n_datasets_with_survival} with survival data):"
            ]
            for gene in result.common_survival_genes[:10]:
                hr = gene.avg_hazard_ratio
                p = gene.avg_cox_p_value
                direction = gene.predominant_risk
                symbol = gene.gene_symbol or gene.gene_id
                lines.append(
                    f"  - {symbol}: HR={hr:.2f}, p={p:.4f}, risk={direction}, "
                    f"n={gene.n_datasets} datasets"
                )
            return "\n".join(lines)
        except Exception as exc:
            logger.warning(f"run_survival_analysis tool failed: {exc}")
            return f"Analysis failed: {exc}"

    @tool
    async def get_gene_info(gene_symbol: str) -> str:
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

    return [
        search_known_datasets,
        estimate_query,
        search_geo_datasets,
        get_gene_info,
    ]
