"""
Response models for GEO Survival Analysis API
"""

from pydantic import BaseModel
from typing import List, Optional


class KMCurveData(BaseModel):
    """Kaplan-Meier curve data for one expression group"""
    times: List[float]
    survival_probabilities: List[float]
    ci_lower: Optional[List[float]] = None
    ci_upper: Optional[List[float]] = None
    n_samples: int
    n_events: int


class HeterogeneityStats(BaseModel):
    """Meta-analysis heterogeneity statistics across datasets"""
    q_statistic: Optional[float] = None
    i_squared: Optional[float] = None      # 0-100 scale
    p_heterogeneity: Optional[float] = None
    tau_squared: Optional[float] = None


class TreatmentArmResult(BaseModel):
    """Expression hazard ratio within one treatment arm (predictive biomarker view)."""
    name: str                              # e.g. "Treated", "Untreated/control"
    hazard_ratio: float
    ci_lower: float
    ci_upper: float
    n_samples: int
    n_events: int


class GeneDatasetResult(BaseModel):
    """Survival analysis result for a gene in a specific dataset"""
    dataset_id: str
    dataset_title: str
    hazard_ratio: float
    hazard_ratio_ci_lower: float
    hazard_ratio_ci_upper: float
    cox_p_value: float
    log_rank_p_value: float
    risk_direction: str  # "high_risk" or "low_risk"
    n_samples: int
    median_survival_high: Optional[float] = None
    median_survival_low: Optional[float] = None
    # KM curve data for visualization
    km_curve_high: Optional[KMCurveData] = None
    km_curve_low: Optional[KMCurveData] = None
    # Multivariate Cox results (F13)
    adjusted_hazard_ratio: Optional[float] = None
    multivariate_cox_p: Optional[float] = None
    covariates_used: Optional[List[str]] = None
    # Predictive (treatment-effect-modifying) biomarker results (F16b).
    # interaction_p_value < 0.05 ⇒ the gene's effect differs by treatment arm.
    interaction_p_value: Optional[float] = None
    treatment_arms: Optional[List[TreatmentArmResult]] = None
    is_predictive: bool = False


class GeneSurvivalResponse(BaseModel):
    """Response model for survival-associated gene with per-dataset results"""

    gene_id: str
    gene_symbol: Optional[str]
    n_datasets: int
    avg_hazard_ratio: float
    avg_cox_p_value: float
    avg_log_rank_p_value: float
    predominant_risk: str  # "high_risk" or "low_risk"
    risk_direction_consistency: float
    datasets: List[str]
    # Per-dataset detailed results for meta-analysis view
    per_dataset_results: Optional[List[GeneDatasetResult]] = None
    # Cross-dataset heterogeneity statistics (F16)
    heterogeneity_stats: Optional[HeterogeneityStats] = None
    # Predictive (treatment-effect-modifying) summary across cohorts (F16b).
    # A gene is flagged predictive when its expression x treatment interaction is
    # significant in at least one cohort with a usable treatment column.
    is_predictive: bool = False
    n_predictive_datasets: int = 0
    min_interaction_p_value: Optional[float] = None


class AnalysisDiagnostics(BaseModel):
    """Diagnostic information for empty results"""

    datasets_analyzed: int
    datasets_with_genes: int
    cancer_filter_enabled: bool = False
    min_occurrence_threshold: int = 2
    reason: Optional[str] = None


class AnalysisResponse(BaseModel):
    """Response model for survival analysis results"""

    query: str
    n_datasets_analyzed: int
    n_datasets_with_survival: int
    common_genes: List[GeneSurvivalResponse]
    processing_time: float
    timestamp: str
    # Ranking feedback for user
    ranking_quality_score: Optional[float] = None
    ranking_recommendations: Optional[str] = None
    # Persistent result ID (F07) — set after DB save, enables shareable URLs
    result_id: Optional[str] = None
    # Diagnostic info when 0 genes found
    diagnostics: Optional[AnalysisDiagnostics] = None


class HealthResponse(BaseModel):
    """Response model for health check"""

    status: str
    version: str
