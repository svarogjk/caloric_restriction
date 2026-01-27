"""
Query Estimation Service.

Evaluates survival analysis queries before execution to:
1. Estimate likelihood of finding relevant data
2. Suggest improvements to increase success
3. Provide confidence scores
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Optional

from pydantic import BaseModel, Field
from pydantic_ai import Agent

from app.models.llm_models import model_dict

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

    def __init__(self, model: str = "mistral"):
        self.model = model
        self._init_estimation_agent()

    def _init_estimation_agent(self) -> None:
        """Initialize the AI estimation agent."""
        self.agent = Agent(
            model=model_dict.get(self.model, model_dict["mistral"]),
            output_type=AIEstimationResult,
            system_prompt=self._get_system_prompt(),
            retries=2,
        )

    def _get_system_prompt(self) -> str:
        """Get the system prompt for estimation."""
        return """You are a bioinformatics expert evaluating survival analysis queries for GEO datasets.

Given a query, estimate:
1. How likely it is to find relevant GEO datasets with survival data (0.0 to 1.0)
2. Estimated number of datasets that might match (0-100)
3. Estimated analysis time in seconds (30-600)

Consider:
- Specificity of the cancer type or disease
- Presence of clinical/survival terminology
- Common availability of such data in GEO
- Technical feasibility of the analysis

High confidence (0.7-1.0): Well-known cancer types with common survival studies
Medium confidence (0.4-0.7): Less common diseases or vague queries
Low confidence (0.0-0.4): Rare diseases, missing context, or infeasible queries

Be realistic - not all queries will find good survival data."""

    async def estimate_query(self, query: str) -> EstimationResult:
        """
        Estimate the success likelihood for a survival analysis query.

        Args:
            query: The user's search query

        Returns:
            EstimationResult with confidence score, suggestions, and improved query
        """
        # 1. Rule-based validation
        validation = self._validate_query(query)

        # 2. AI-powered estimation
        ai_estimation = await self._ai_estimate(query)

        # 3. Calculate combined confidence score
        confidence = self._calculate_confidence(validation, ai_estimation)

        # 4. Generate improvement suggestions
        suggestions = self._generate_suggestions(validation, query)

        # 5. Create improved query if confidence is low
        improved_query = None
        if confidence < 0.5 and suggestions:
            improved_query = await self._improve_query(query, suggestions)

        # 6. Determine if analysis can proceed
        can_proceed = confidence >= 0.3

        return EstimationResult(
            confidence_score=confidence,
            estimated_datasets=ai_estimation.estimated_datasets,
            estimated_time_seconds=ai_estimation.estimated_time,
            can_proceed=can_proceed,
            suggestions=suggestions,
            improved_query=improved_query,
            validation=validation,
        )

    def _validate_query(self, query: str) -> dict:
        """Perform rule-based query validation."""
        query_lower = query.lower()

        # Check for survival keywords
        has_survival = any(kw in query_lower for kw in self.SURVIVAL_KEYWORDS)

        # Check for cancer type
        has_cancer = any(ct in query_lower for ct in self.CANCER_TYPES)

        # Check for organism
        has_organism = any(org in query_lower for org in self.ORGANISMS)

        # Check for gene focus
        has_gene_focus = any(term in query_lower for term in self.GENE_TERMS)

        # Query length validation
        query_length_ok = 10 < len(query) < 500

        return {
            "has_survival_keywords": has_survival,
            "has_cancer_type": has_cancer,
            "has_organism": has_organism,
            "has_gene_focus": has_gene_focus,
            "query_length_ok": query_length_ok,
        }

    async def _ai_estimate(self, query: str) -> AIEstimationResult:
        """Get AI-powered estimation."""
        try:
            prompt = f"""Evaluate this survival analysis query for GEO datasets:

Query: "{query}"

Consider:
- Is this a well-studied disease with available survival data?
- How specific is the query?
- What's the likelihood of finding matching datasets?

Provide your estimation."""

            result = await self.agent.run(prompt)
            return result.output

        except Exception as e:
            logger.warning(f"AI estimation failed: {e}")
            # Return conservative default
            return AIEstimationResult(
                confidence=0.5,
                estimated_datasets=5,
                estimated_time=120,
                rationale="Default estimation due to AI service error",
            )

    def _calculate_confidence(
        self, validation: dict, ai_estimation: AIEstimationResult
    ) -> float:
        """Calculate overall confidence score."""
        score = 0.0

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

    def _generate_suggestions(self, validation: dict, query: str) -> list[str]:
        """Generate improvement suggestions based on validation."""
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

        if not validation["has_organism"]:
            suggestions.append(
                "Consider specifying the organism (e.g., 'human' for cancer studies, "
                "'mouse' for aging studies)"
            )

        if not validation["has_gene_focus"]:
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
