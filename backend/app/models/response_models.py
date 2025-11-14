"""
Response models for GEO Analysis API
"""

from pydantic import BaseModel
from typing import List


class GeneOccurrenceResponse(BaseModel):
    """Response model for gene occurrence"""
    
    gene_id: str
    n_datasets: int
    avg_log_fc: float
    direction_consistency: float
    datasets: List[str]


class AnalysisResponse(BaseModel):
    """Response model for analysis results"""
    
    query: str
    n_datasets_analyzed: int
    n_datasets_with_degs: int
    common_genes: List[GeneOccurrenceResponse]
    processing_time: float
    timestamp: str


class HealthResponse(BaseModel):
    """Response model for health check"""
    
    status: str
    version: str
