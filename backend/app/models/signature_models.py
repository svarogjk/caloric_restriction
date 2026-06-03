"""
Models for the validated multi-gene prognostic signature (F17) and the
downstream features that consume the locked model artifact:

    F17 — build/validate signature (this is the producer)
    F18 — clinical nomogram (reads `genes` coefficients)
    F19 — established-signature concordance (reads `genes` symbols/directions)
    F23 — single-sample risk scoring (reads everything: coefficients,
          reference distributions, tertile cutoffs, reference KM)

The `PrognosticModel` below is the single "locked artifact" schema. It is
designed once here so all four features share it — do not fork it per feature.

Positioning guardrail (see clinical-positioning skill §2, §7): everything here
is PROGNOSTIC (predicts outcome/survival), never PREDICTIVE of drug response,
and is research-use-only.
"""

from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


RUO_DISCLAIMER = (
    "Research use only. This prognostic signature estimates outcome risk from "
    "tumour gene expression; it does not predict response to any specific therapy "
    "and is not a clinical decision-making device."
)


# ==================== Locked model artifact ====================

class SignatureGene(BaseModel):
    """One gene in the locked signature."""
    gene_symbol: str
    coefficient: float          # Cox coefficient (log-HR) on z-scored expression
    hazard_ratio: float         # exp(coefficient), per +1 SD of expression
    ref_mean: float             # training-cohort raw mean (for reference/z-scoring)
    ref_std: float              # training-cohort raw std
    ref_quantiles: List[float]  # 101 sorted reference values (percentiles 0..100)


class ReferenceKMCurve(BaseModel):
    """Reference Kaplan-Meier curve for one risk group, from the training cohort."""
    group: str                  # "low" | "intermediate" | "high"
    times: List[float]
    survival_probabilities: List[float]
    n_samples: int
    n_events: int


class CohortValidation(BaseModel):
    """Per-cohort discrimination (Harrell's C-index)."""
    accession: str
    role: str                   # "training" | "validation"
    n_samples: int
    n_events: int
    c_index: float


class PrognosticModel(BaseModel):
    """
    The locked, version-pinned prognostic model artifact.
    Producer: F17. Consumers: F18, F19, F23.
    """
    model_id: str
    query: str
    cancer_type: Optional[str] = None
    version: str = "1.0.0"
    created_at: str
    time_unit: str = "days"

    genes: List[SignatureGene]
    risk_score_tertiles: List[float]        # [t1, t2] cutoffs on training risk scores
    risk_score_quantiles: List[float]       # 101 sorted training risk scores (percentiles)
    reference_km: List[ReferenceKMCurve]

    training_accession: str
    n_training_samples: int
    cohort_validations: List[CohortValidation]
    pooled_c_index: float                   # sample-weighted mean C-index across validation cohorts

    is_demo: bool = False
    disclaimer: str = RUO_DISCLAIMER


# ==================== Request / response models ====================

class SignatureRequest(BaseModel):
    """Build a prognostic signature. Either reuse a saved analysis or run the demo."""
    result_id: Optional[str] = Field(
        default=None,
        description="Saved analysis result to derive candidate genes + cohorts from",
    )
    query: Optional[str] = Field(
        default=None,
        description="Cancer-type / study query (used for labelling; required if no result_id)",
    )
    max_genes: int = Field(default=15, ge=2, le=50, description="Max genes in the signature")
    demo: bool = Field(
        default=False,
        description="Build a deterministic synthetic demo signature (no GEO data required)",
    )


class PredictRequest(BaseModel):
    """Single-sample prognostic scoring (F23), research-use-only, in-memory only."""
    model_id: str
    expression: dict[str, float] = Field(
        ...,
        description="Map of gene_symbol -> expression value for ONE tumour sample",
    )


class PredictResponse(BaseModel):
    model_id: str
    risk_score: float
    risk_group: str                         # "low" | "intermediate" | "high"
    risk_percentile: float                  # 0-100 vs training reference
    genes_used: int
    genes_total: int
    reference_km: ReferenceKMCurve          # the assigned group's reference curve
    predicted_survival: List["SurvivalAtHorizon"]
    pooled_c_index: float
    disclaimer: str = RUO_DISCLAIMER


class SurvivalAtHorizon(BaseModel):
    horizon_label: str                      # e.g. "1-year"
    time: float
    survival_probability: float


PredictResponse.model_rebuild()
