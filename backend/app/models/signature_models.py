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


class ClinicalCovariate(BaseModel):
    """One clinical covariate in the combined (clinical + expression) Cox model.

    The combined linear predictor adds each covariate's contribution on top of
    the expression risk score:
      - numeric (e.g. age):      contribution = coefficient * (value - ref_mean) / ref_std
      - categorical (e.g. grade): contribution = category_coefficients[value]
        (the dropped `reference_category` contributes 0)

    `display_label`, `options`, `min_value`, `max_value` drive the dynamically
    generated patient-intake form in Oncologist Mode.
    """
    name: str                                       # raw training metadata column
    display_label: str                              # human label for the intake form
    kind: str                                       # "numeric" | "categorical"
    coefficient: float = 0.0                        # numeric: Cox coef on standardized value
    ref_mean: float = 0.0                           # numeric reference mean
    ref_std: float = 1.0                            # numeric reference std (never 0)
    category_coefficients: dict[str, float] = Field(default_factory=dict)  # level -> coef
    reference_category: Optional[str] = None        # dropped (baseline) categorical level
    options: Optional[List[str]] = None             # categorical selectable levels
    min_value: Optional[float] = None               # numeric form hint
    max_value: Optional[float] = None
    required: bool = False


class RiskContribution(BaseModel):
    """Additive contribution of one term to the (combined) linear predictor —
    powers the clinician-legible 'why' breakdown in the readout."""
    label: str                                      # "Expression signature" | "Age" | "Grade = 3"
    contribution: float
    kind: str                                       # "expression" | "clinical"


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
    # Expression-only reference (also the fallback when a patient gives no clinical data).
    risk_score_tertiles: List[float]        # [t1, t2] cutoffs on training EXPRESSION risk scores
    risk_score_quantiles: List[float]       # 101 sorted training expression risk scores
    reference_km: List[ReferenceKMCurve]
    # Pooled distribution of ALL training expression values (sorted quantiles) — the
    # reference for cross-platform single-sample quantile normalization (F23).
    reference_pooled_quantiles: Optional[List[float]] = None

    training_accession: str
    n_training_samples: int
    cohort_validations: List[CohortValidation]
    pooled_c_index: float                   # headline C-index (combined if covariates exist, else expression-only)

    # ---- Combined clinical + expression model (empty/None ⇒ expression-only) ----
    clinical_covariates: List[ClinicalCovariate] = Field(default_factory=list)
    expression_score_coefficient: float = 1.0   # β of the expression risk score in the combined Cox
    # Combined-score reference distribution (used when the patient supplies clinical fields):
    combined_risk_tertiles: Optional[List[float]] = None
    combined_risk_quantiles: Optional[List[float]] = None
    combined_reference_km: Optional[List[ReferenceKMCurve]] = None
    # Incremental-value rigor metrics (validation cohorts):
    c_index_expression_only: Optional[float] = None
    c_index_clinical_only: Optional[float] = None
    c_index_combined: Optional[float] = None
    delta_c_index: Optional[float] = None        # combined − expression-only

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
    clinical: Optional[dict[str, float | str]] = Field(
        default=None,
        description="Optional clinical covariates (e.g. {'age': 64, 'grade': '3'}); "
        "when omitted the sample is scored on expression only.",
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
    # Combined-model extras (degrade gracefully for expression-only models):
    scored_on: str = "expression-only"      # "combined" | "expression-only" | "expression-only (clinical omitted)"
    normalization: str = ""                 # how expression was put on the reference scale
    warnings: List[str] = Field(default_factory=list)  # coverage / scale / covariate caveats
    contributions: List["RiskContribution"] = Field(default_factory=list)
    c_index_expression_only: Optional[float] = None
    c_index_clinical_only: Optional[float] = None
    c_index_combined: Optional[float] = None
    delta_c_index: Optional[float] = None
    disclaimer: str = RUO_DISCLAIMER


class SurvivalAtHorizon(BaseModel):
    horizon_label: str                      # e.g. "1-year"
    time: float
    survival_probability: float


PredictResponse.model_rebuild()
