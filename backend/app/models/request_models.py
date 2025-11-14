"""
Request models for GEO Analysis API
"""

from pydantic import BaseModel, Field
from typing import Optional


class AnalysisRequest(BaseModel):
    """Request model for GEO analysis"""
    
    query: str = Field(
        ...,
        description="Search query (e.g., 'caloric restriction aging')",
        min_length=1,
        max_length=500
    )
    max_datasets: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of datasets to analyze"
    )
    organism: Optional[str] = Field(
        default="Mus musculus",
        description="Filter by organism"
    )
    min_occurrence: int = Field(
        default=2,
        ge=1,
        le=50,
        description="Minimum datasets where gene must appear"
    )
