"""
Request models for GEO Analysis API
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List


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
    gene_filter: Optional[List[str]] = Field(
        default=None,
        max_length=500,
        description="Optional list of gene symbols to restrict analysis to (batch mode)"
    )

    @field_validator("gene_filter", mode="before")
    @classmethod
    def normalize_gene_filter(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is None:
            return None
        if len(v) > 500:
            raise ValueError("gene_filter may contain at most 500 gene symbols")
        return [symbol.strip().upper() for symbol in v if symbol.strip()]
