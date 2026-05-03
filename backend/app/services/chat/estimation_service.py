"""
Query Estimation Service.

Evaluates survival analysis queries before execution to:
1. Estimate likelihood of finding relevant data
2. Suggest improvements to increase success
3. Provide confidence scores
4. Preview actual GEO search results for data-driven feedback
"""

import asyncio
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.mistral import MistralModel
from pydantic_ai.providers.mistral import MistralProvider
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.providers.anthropic import AnthropicProvider

_SERVICES_DIR = Path(__file__).parent.parent

logger = logging.getLogger(__name__)


class AIEstimationResult(BaseModel):
    """Structured output from AI estimation."""

    confidence: float = Field(
        ge=0.0, le=1.0, description="Confidence score for query success"
    )
    estimated_datasets: int = Field(
        ge=0, description="Estimated number of matching datasets"
    )
    estimated_time: float = Field(
        ge=0, description="Estimated analysis time in seconds"
    )
    rationale: str = Field(description="Brief explanation of the estimation")


@dataclass
class EstimationResult:
    """Complete estimation result with suggestions."""

    confidence_score: float
    estimated_datasets: int
    estimated_time_seconds: float
    can_proceed: bool
    suggestions: list[str]
    improved_query: Optional[str]
    validation: dict = field(default_factory=dict)
    geo_preview: Optional[dict] = None  # GEO preview data if available


class QueryEstimationService:
    """Service for estimating query success likelihood."""

    # Survival-related keywords
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
    }

    # Common cancer types with known GEO datasets
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

    # Organism identifiers
    ORGANISMS = {
        "human",
        "homo sapiens",
        "mouse",
        "mus musculus",
        "rat",
        "rattus norvegicus",
    }

    # Gene-related terms
    GENE_TERMS = {
        "gene",
        "genes",
        "expression",
        "biomarker",
        "biomarkers",
        "marker",
        "markers",
        "transcript",
        "mrna",
        "rna",
    }

    def __init__(
        self,
        model: str = "mistral",
        geo_preview_service: Optional[Any] = None,
    ):
        self.model = model
        self.geo_preview_service = geo_preview_service
        self._agents = self._init_agents()

    _ESTIMATION_SYSTEM_PROMPT = (
        "You are a query estimation assistant for a bioinformatics tool. "
        "Evaluate survival analysis queries for GEO datasets and return "
        "structured confidence estimates."
    )

    def _init_agents(self) -> dict[str, Agent]:
        """Initialize estimation agents for all available LLM providers."""
        agents: dict[str, Agent] = {}

        mistral_key = os.getenv("MISTRAL_KEY", "")
        if not mistral_key:
            key_file = _SERVICES_DIR / "mistral_key.txt"
            if key_file.exists():
                mistral_key = key_file.read_text().strip()
        if mistral_key:
            agents["mistral"] = Agent(
                MistralModel("mistral-small-latest", provider=MistralProvider(api_key=mistral_key)),
                output_type=AIEstimationResult,
                system_prompt=self._ESTIMATION_SYSTEM_PROMPT,
            )

        anthropic_key = os.getenv("ANTHROPIC_KEY", "")
        if not anthropic_key:
            key_file = _SERVICES_DIR / "anthropic_key.txt"
            if key_file.exists():
                anthropic_key = key_file.read_text().strip()
        if anthropic_key:
            agents["anthropic"] = Agent(
                AnthropicModel("claude-haiku-4-5-20251001", provider=AnthropicProvider(api_key=anthropic_key)),
                output_type=AIEstimationResult,
                system_prompt=self._ESTIMATION_SYSTEM_PROMPT,
            )

        return agents

    async def estimate_query(
        self,
        query: str,
        user_settings: Optional[dict] = None,
        model: str = "mistral",
    ) -> EstimationResult:
        """
        Estimate the success likelihood for a survival analysis query.

        Args:
            query: The user's search query
            user_settings: User's pre-configured settings (organism, cancer_genes_only, etc.)

        Returns:
            EstimationResult with confidence score, suggestions, and improved query
        """
        # 1. Rule-based validation (fast, synchronous)
        # Treat pre-configured user settings as equivalent to query keywords
        validation = self._validate_query(query, user_settings)

        # 2. Run AI estimation and GEO preview in parallel
        geo_preview = None
        geo_preview_dict = None

        if self.geo_preview_service:
            # Run both in parallel for better performance
            try:
                # Wrap with timeouts: GEO preview 15s, AI estimation 20s
                geo_task = asyncio.wait_for(
                    self.geo_preview_service.get_preview(query), timeout=15.0
                )
                ai_task = asyncio.wait_for(self._ai_estimate(query, model), timeout=20.0)
                geo_preview, ai_estimation = await asyncio.gather(
                    geo_task, ai_task, return_exceptions=True
                )

                # Handle any exceptions from gather
                if isinstance(geo_preview, Exception):
                    logger.warning(f"GEO preview failed: {geo_preview}")
                    geo_preview = None
                if isinstance(ai_estimation, Exception):
                    logger.warning(f"AI estimation failed: {ai_estimation}")
                    ai_estimation = AIEstimationResult(
                        confidence=0.5,
                        estimated_datasets=5,
                        estimated_time=120,
                        rationale="Default estimation due to error",
                    )
            except Exception as e:
                logger.warning(f"Parallel estimation failed: {e}")
                ai_estimation = await self._ai_estimate(query, model)
        else:
            # No GEO preview service, just run AI estimation
            ai_estimation = await self._ai_estimate(query, model)

        # 3. Convert geo_preview to dict if available
        if geo_preview:
            geo_preview_dict = self.geo_preview_service.preview_to_dict(geo_preview)

        # 4. Calculate combined confidence score (with GEO data if available)
        confidence = self._calculate_confidence(
            validation, ai_estimation, geo_preview_dict
        )

        # 5. Generate improvement suggestions (combining rule-based and data-driven)
        suggestions = self._generate_suggestions(validation, query, user_settings)

        # Add data-driven suggestions from GEO preview
        if geo_preview and self.geo_preview_service:
            data_suggestions = self.geo_preview_service.generate_data_driven_suggestions(
                geo_preview, query
            )
            # Merge without duplicates, data-driven first
            seen = set()
            merged = []
            for s in data_suggestions + suggestions:
                s_key = s[:50].lower()  # Use first 50 chars as key
                if s_key not in seen:
                    seen.add(s_key)
                    merged.append(s)
            suggestions = merged[:6]  # Limit to 6 suggestions

        # 6. Create improved query if confidence is low
        improved_query = None
        if confidence < 0.5 and suggestions:
            improved_query = await self._improve_query(query, suggestions)

        # 7. Determine if analysis can proceed
        can_proceed = confidence >= 0.3

        # Use actual dataset count from GEO if available
        estimated_datasets = ai_estimation.estimated_datasets
        if geo_preview_dict and geo_preview_dict.get("total_datasets", 0) > 0:
            estimated_datasets = geo_preview_dict["total_datasets"]

        return EstimationResult(
            confidence_score=confidence,
            estimated_datasets=estimated_datasets,
            estimated_time_seconds=ai_estimation.estimated_time,
            can_proceed=can_proceed,
            suggestions=suggestions,
            improved_query=improved_query,
            validation=validation,
            geo_preview=geo_preview_dict,
        )

    def _validate_query(
        self, query: str, user_settings: Optional[dict] = None
    ) -> dict:
        """Perform rule-based query validation."""
        query_lower = query.lower()

        # Check for survival keywords
        has_survival = any(kw in query_lower for kw in self.SURVIVAL_KEYWORDS)

        # Check for cancer type
        has_cancer = any(ct in query_lower for ct in self.CANCER_TYPES)

        # Check for organism — treat pre-configured user setting as present
        has_organism = any(org in query_lower for org in self.ORGANISMS)
        if not has_organism and user_settings and user_settings.get("organism"):
            has_organism = True

        # Check for gene focus — treat candidate_genes or cancer_genes_only as present
        has_gene_focus = any(term in query_lower for term in self.GENE_TERMS)
        if not has_gene_focus and user_settings:
            if user_settings.get("candidate_genes") or user_settings.get("cancer_genes_only"):
                has_gene_focus = True

        # Query length validation
        query_length_ok = 10 < len(query) < 500

        return {
            "has_survival_keywords": has_survival,
            "has_cancer_type": has_cancer,
            "has_organism": has_organism,
            "has_gene_focus": has_gene_focus,
            "query_length_ok": query_length_ok,
        }

    async def _ai_estimate(self, query: str, model: str = "mistral") -> AIEstimationResult:
        """Get AI-powered estimation using PydanticAI structured output."""
        agent = self._agents.get(model) or self._agents.get("mistral") or next(iter(self._agents.values()), None)
        if agent is None:
            raise RuntimeError("No estimation agent available — check API keys")
        prompt = (
            f'Evaluate this survival analysis query for GEO datasets:\n\nQuery: "{query}"\n\n'
            "Consider:\n"
            "- Is this a well-studied disease with available survival data?\n"
            "- How specific is the query?\n"
            "- What's the likelihood of finding matching datasets?\n\n"
            "Provide your estimation."
        )
        try:
            result = await agent.run(prompt)
            return result.output
        except (ValueError, RuntimeError) as exc:
            logger.warning(f"AI estimation failed: {exc}")
            return AIEstimationResult(
                confidence=0.5,
                estimated_datasets=5,
                estimated_time=120,
                rationale="Default estimation due to AI service error",
            )

    def _calculate_confidence(
        self,
        validation: dict,
        ai_estimation: AIEstimationResult,
        geo_preview: Optional[dict] = None,
    ) -> float:
        """
        Calculate overall confidence score.

        Incorporates rule-based validation, AI estimation, and real GEO data.

        Args:
            validation: Rule-based validation results
            ai_estimation: AI-powered estimation
            geo_preview: Optional GEO preview data

        Returns:
            Confidence score between 0.0 and 1.0
        """
        score = 0.0

        if geo_preview and geo_preview.get("total_datasets", 0) > 0:
            # Data-driven confidence (when GEO preview is available)
            # Use real data to inform confidence (50% weight)
            total = geo_preview["total_datasets"]
            survival_count = geo_preview.get("datasets_with_survival_keywords", 0)
            platform_diversity = geo_preview.get("platform_diversity", "high")

            # Dataset count factors
            if total >= 50:
                score += 0.15
            elif total >= 20:
                score += 0.12
            elif total >= 10:
                score += 0.08
            elif total >= 5:
                score += 0.05

            # Survival keyword presence in datasets
            preview_count = len(geo_preview.get("top_datasets", []))
            if preview_count > 0:
                survival_ratio = survival_count / preview_count
                if survival_ratio >= 0.5:
                    score += 0.12
                elif survival_ratio >= 0.3:
                    score += 0.08
                elif survival_ratio > 0:
                    score += 0.04

            # Platform homogeneity bonus
            if platform_diversity == "low":
                score += 0.08
            elif platform_diversity == "medium":
                score += 0.04
            # High diversity = no bonus, harder to get common genes

            # Rule-based validation (25% weight)
            if validation["has_survival_keywords"]:
                score += 0.06
            if validation["has_cancer_type"]:
                score += 0.08
            if validation["has_gene_focus"]:
                score += 0.04
            if validation["has_organism"]:
                score += 0.02

            # AI estimation (25% weight)
            score += ai_estimation.confidence * 0.25

        else:
            # Fallback: No GEO preview, use original logic
            # Rule-based factors (40% weight)
            if validation["has_survival_keywords"]:
                score += 0.12
            if validation["has_cancer_type"]:
                score += 0.15
            if validation["has_gene_focus"]:
                score += 0.08
            if validation["has_organism"]:
                score += 0.05

            # AI estimation factor (60% weight)
            score += ai_estimation.confidence * 0.6

        return min(1.0, max(0.0, score))

    def _generate_suggestions(
        self,
        validation: dict,
        query: str,
        user_settings: Optional[dict] = None,
    ) -> list[str]:
        """Generate improvement suggestions based on validation."""
        settings = user_settings or {}
        organism_configured = bool(settings.get("organism"))
        genes_configured = bool(settings.get("candidate_genes") or settings.get("cancer_genes_only"))

        suggestions = []

        if not validation["has_survival_keywords"]:
            suggestions.append(
                "Add survival-related terms like 'overall survival', 'prognosis', "
                "or 'clinical outcome' to find datasets with survival data"
            )

        if not validation["has_cancer_type"]:
            suggestions.append(
                "Specify a cancer type (e.g., 'breast cancer', 'lung cancer') "
                "for more targeted results"
            )

        # Only suggest organism if it is NOT already configured in user settings
        if not validation["has_organism"] and not organism_configured:
            suggestions.append(
                "Consider specifying the organism (e.g., 'human' for cancer studies, "
                "'mouse' for aging studies)"
            )

        # Only suggest gene focus if candidate genes are NOT already configured
        if not validation["has_gene_focus"] and not genes_configured:
            suggestions.append(
                "Adding terms like 'gene expression' or 'biomarker' may help "
                "find relevant expression datasets"
            )

        if not validation["query_length_ok"]:
            if len(query) < 10:
                suggestions.append("Provide a more detailed query with specific terms")
            else:
                suggestions.append(
                    "Consider simplifying your query to focus on key concepts"
                )

        return suggestions

    async def _improve_query(
        self, original_query: str, suggestions: list[str]
    ) -> Optional[str]:
        """Generate an improved query based on suggestions."""
        # Simple rule-based improvement
        improved = original_query

        # Add survival context if missing
        if "survival" not in original_query.lower():
            improved = f"{improved} survival prognosis"

        # Add human organism if no organism specified
        organisms = ["human", "mouse", "homo sapiens", "mus musculus"]
        if not any(org in original_query.lower() for org in organisms):
            improved = f"{improved} human"

        # Clean up extra spaces
        improved = re.sub(r"\s+", " ", improved).strip()

        # Only return if different from original
        if improved.lower() != original_query.lower():
            return improved

        return None
