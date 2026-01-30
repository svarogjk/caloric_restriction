"""
GEO Preview Service.

Provides quick GEO search previews to estimate query success
before running expensive survival analysis.
"""

import logging
from dataclasses import asdict
from typing import Optional

from app.services.geo_client import GEOClient, GEOPreviewResult

logger = logging.getLogger(__name__)


class GEOPreviewService:
    """
    Service for getting quick GEO search previews.

    Uses GEOClient to search GEO and analyze results for survival
    analysis potential without running full analysis.
    """

    # Survival-related keywords to look for in dataset descriptions
    SURVIVAL_KEYWORDS = {
        "survival",
        "overall survival",
        "os",
        "prognosis",
        "prognostic",
        "outcome",
        "clinical outcome",
        "patient outcome",
        "mortality",
        "death",
        "follow-up",
        "time to event",
        "hazard",
        "relapse",
        "recurrence",
        "progression",
        "disease-free",
        "event-free",
        "dfs",
        "pfs",
        "rfs",
        "efs",
    }

    # Cancer types for query analysis
    CANCER_TYPES = {
        "breast cancer",
        "lung cancer",
        "colorectal cancer",
        "colon cancer",
        "ovarian cancer",
        "gastric cancer",
        "stomach cancer",
        "glioblastoma",
        "glioma",
        "brain cancer",
        "hepatocellular carcinoma",
        "liver cancer",
        "pancreatic cancer",
        "prostate cancer",
        "melanoma",
        "leukemia",
        "lymphoma",
        "renal cell carcinoma",
        "kidney cancer",
        "bladder cancer",
        "esophageal cancer",
        "head and neck cancer",
        "thyroid cancer",
        "neuroblastoma",
        "sarcoma",
    }

    def __init__(self, geo_client: Optional[GEOClient] = None):
        """
        Initialize the GEO preview service.

        Args:
            geo_client: Optional GEOClient instance. If not provided,
                       a new one will be created.
        """
        self.geo_client = geo_client

    async def _get_client(self) -> GEOClient:
        """Get or create a GEO client."""
        if self.geo_client is None:
            self.geo_client = GEOClient()
        return self.geo_client

    async def get_preview(
        self,
        query: str,
        organism: Optional[str] = "Homo sapiens",
        max_preview: int = 10,
    ) -> GEOPreviewResult:
        """
        Get a quick preview of GEO search results.

        Args:
            query: User's search query
            organism: Filter by organism (default: human)
            max_preview: Maximum datasets to preview

        Returns:
            GEOPreviewResult with dataset counts, previews, and warnings
        """
        client = await self._get_client()

        # Parse query into keywords
        keywords = self._parse_query_keywords(query)

        logger.info(f"GEO preview for query: {query}")
        logger.info(f"Parsed keywords: {keywords}")

        try:
            # Get preview from GEO
            preview = await client.get_preview(
                keywords=keywords,
                organism=organism,
                min_samples=30,
                max_preview=max_preview,
                survival_keywords=self.SURVIVAL_KEYWORDS,
            )

            logger.info(
                f"GEO preview result: {preview.total_datasets} datasets, "
                f"{preview.datasets_with_survival_keywords} with survival keywords"
            )

            return preview

        except Exception as e:
            logger.error(f"Error getting GEO preview: {e}")
            # Return empty result on error
            return GEOPreviewResult(
                total_datasets=0,
                datasets_with_survival_keywords=0,
                top_datasets=[],
                platform_counts={},
                platform_diversity="low",
                warnings=[f"Unable to search GEO: {str(e)}"],
                search_query=query,
            )

    def _parse_query_keywords(self, query: str) -> list[str]:
        """
        Parse a natural language query into search keywords.

        Args:
            query: User's search query

        Returns:
            List of keywords for GEO search
        """
        query_lower = query.lower()
        keywords = []

        # Check for cancer types
        for cancer in self.CANCER_TYPES:
            if cancer in query_lower:
                keywords.append(cancer)
                # Also add variant forms
                if "cancer" in cancer:
                    keywords.append(cancer.replace("cancer", "carcinoma"))
                break

        # Add survival-related keywords if present
        for kw in self.SURVIVAL_KEYWORDS:
            if kw in query_lower and kw not in keywords:
                keywords.append(kw)

        # If no specific keywords found, use key phrases from query
        if not keywords:
            # Split query and filter common words
            stop_words = {
                "what",
                "which",
                "how",
                "does",
                "do",
                "the",
                "a",
                "an",
                "in",
                "for",
                "to",
                "of",
                "and",
                "or",
                "that",
                "this",
                "are",
                "is",
                "be",
                "can",
                "with",
                "from",
                "genes",
                "gene",
                "predict",
                "associated",
                "related",
                "patients",
            }
            words = query_lower.split()
            keywords = [w for w in words if w not in stop_words and len(w) > 2]

        # Always add survival if not present and query seems survival-related
        survival_related = any(
            term in query_lower
            for term in ["survival", "prognosis", "outcome", "death", "mortality"]
        )
        if survival_related and "survival" not in keywords:
            keywords.append("survival")

        # Ensure we have at least some keywords
        if not keywords:
            keywords = ["expression", "profiling"]

        return keywords[:10]  # Limit to 10 keywords

    def preview_to_dict(self, preview: GEOPreviewResult) -> dict:
        """
        Convert GEOPreviewResult to a dictionary for JSON serialization.

        Args:
            preview: GEOPreviewResult instance

        Returns:
            Dictionary representation
        """
        return {
            "total_datasets": preview.total_datasets,
            "datasets_with_survival_keywords": preview.datasets_with_survival_keywords,
            "top_datasets": [asdict(ds) for ds in preview.top_datasets],
            "platform_counts": preview.platform_counts,
            "platform_diversity": preview.platform_diversity,
            "warnings": preview.warnings,
            "search_query": preview.search_query,
        }

    def generate_data_driven_suggestions(
        self, preview: GEOPreviewResult, query: str
    ) -> list[str]:
        """
        Generate suggestions based on actual GEO preview data.

        Args:
            preview: GEOPreviewResult from get_preview()
            query: Original user query

        Returns:
            List of actionable suggestions
        """
        suggestions = []
        query_lower = query.lower()

        # No datasets found
        if preview.total_datasets == 0:
            suggestions.append(
                "No datasets found. Try broader terms like 'cancer survival' "
                "or check spelling."
            )
            return suggestions

        # Few datasets with survival keywords
        survival_ratio = (
            preview.datasets_with_survival_keywords / len(preview.top_datasets)
            if preview.top_datasets
            else 0
        )
        if survival_ratio < 0.3:
            suggestions.append(
                f"Only {preview.datasets_with_survival_keywords} of "
                f"{len(preview.top_datasets)} datasets mention survival data. "
                "Add 'survival' or 'prognosis' to your query."
            )

        # Platform diversity suggestions
        if preview.platform_diversity == "high" and preview.platform_counts:
            top_platform = max(preview.platform_counts, key=preview.platform_counts.get)
            top_count = preview.platform_counts[top_platform]
            total = sum(preview.platform_counts.values())
            if top_count > total * 0.4:
                suggestions.append(
                    f"{int(top_count/total*100)}% of datasets use {top_platform}. "
                    f"Add '{top_platform}' to focus on this platform for better gene overlap."
                )
            else:
                suggestions.append(
                    "High platform diversity detected. Consider specifying a platform "
                    "(e.g., 'GPL570' or 'RNA-seq') for consistent gene coverage."
                )

        # Organism suggestion
        if "human" not in query_lower and "homo sapiens" not in query_lower:
            if "mouse" not in query_lower and "mus musculus" not in query_lower:
                suggestions.append(
                    "Specify the organism (e.g., 'human' or 'mouse') "
                    "for more targeted results."
                )

        # Cancer type suggestion
        has_cancer_type = any(ct in query_lower for ct in self.CANCER_TYPES)
        if not has_cancer_type and preview.total_datasets > 100:
            suggestions.append(
                "Many datasets found. Specify a cancer type "
                "(e.g., 'breast cancer', 'lung cancer') for focused results."
            )

        return suggestions
