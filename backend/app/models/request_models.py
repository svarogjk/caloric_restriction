"""
Request models for GEO Analysis API
"""

from pydantic import BaseModel, Field
from typing import Optional


class AnalysisRequest(BaseModel):
    """Request model for GEO survival analysis"""
    
    query: str = Field(
        ...,
        description="Search query (e.g., 'cancer survival prognosis')",
        min_length=1,
        max_length=500
    )
    max_datasets: int = Field(
        default=10,
        ge=1,
        le=1000,
        description="Maximum number of datasets to analyze"
    )
    organism: Optional[str] = Field(
        default=None,
        description="Filter by organism (e.g., 'Homo sapiens', 'Mus musculus')"
    )
    min_occurrence: int = Field(
        default=2,
        ge=1,
        le=50,
        description="Minimum datasets where gene must appear"
    )
    model: str = Field(
        default="mistral",
        description="LLM model to use for analysis ('mistral' or 'claude')"
    )
    ranking_multiplier: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Multiplier for datasets to rank before analysis"
    )
    cancer_genes_only: bool = Field(
        default=False,
        description="Restrict analysis to ~600 most cancer-related genes (COSMIC CGC)"
    )
