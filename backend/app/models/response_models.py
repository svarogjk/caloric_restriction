"""
Response models for GEO Survival Analysis API
"""

from pydantic import BaseModel
from typing import List, Optional, Dict


class KMCurvePoint(BaseModel):
    """Single point on a Kaplan-Meier curve"""
    time: float
    survival_probability: float
    ci_lower: Optional[float] = None
    ci_upper: Optional[float] = None


class KMCurveData(BaseModel):
    """Kaplan-Meier curve data for one expression group"""
    times: List[float]
    survival_probabilities: List[float]
    ci_lower: Optional[List[float]] = None
    ci_upper: Optional[List[float]] = None
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


class AnalysisResponse(BaseModel):
    """Response model for survival analysis results"""
    
    query: str
    n_datasets_analyzed: int
    n_datasets_with_survival: int
    common_genes: List[GeneSurvivalResponse]
    processing_time: float
    timestamp: str


class HealthResponse(BaseModel):
    """Response model for health check"""
    
    status: str
    version: str


# Keep legacy response for backwards compatibility
class GeneOccurrenceResponse(BaseModel):
    """Legacy response model for gene occurrence (deprecated)"""
    
    gene_id: str
    n_datasets: int
    avg_log_fc: float
    avg_p_value: float
    avg_adj_p_value: float
    direction_consistency: float
    datasets: List[str]
