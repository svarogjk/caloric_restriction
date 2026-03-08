"""
Pathway enrichment endpoint wrapping g:Profiler.
"""
import logging
from typing import List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator

from app.services.pathway_enrichment_service import pathway_enrichment_service

logger = logging.getLogger(__name__)

router = APIRouter()


class EnrichmentRequest(BaseModel):
    genes: List[str]
    organism: str = "hsapiens"

    @field_validator("genes")
    @classmethod
    def validate_genes(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("genes list must not be empty")
        if len(v) > 500:
            raise ValueError("Maximum 500 genes per request")
        return [g.strip().upper() for g in v if g.strip()]


class EnrichmentTermResponse(BaseModel):
    term_id: str
    term_name: str
    source: str
    p_value: float
    intersection_size: int
    query_size: int
    term_size: int
    intersection_genes: List[str]


class EnrichmentResponse(BaseModel):
    terms: List[EnrichmentTermResponse]
    query_size: int
    organism: str


@router.post("/enrich", response_model=EnrichmentResponse)
async def run_enrichment(request: EnrichmentRequest):
    """
    Run pathway enrichment analysis via g:Profiler (free API, no key needed).
    Returns GO, KEGG, and Reactome terms enriched in the input gene list.
    """
    try:
        terms = await pathway_enrichment_service.enrich(
            gene_symbols=request.genes,
            organism=request.organism,
        )
        return EnrichmentResponse(
            terms=[
                EnrichmentTermResponse(
                    term_id=t.term_id,
                    term_name=t.term_name,
                    source=t.source,
                    p_value=t.p_value,
                    intersection_size=t.intersection_size,
                    query_size=t.query_size,
                    term_size=t.term_size,
                    intersection_genes=t.intersection_genes,
                )
                for t in terms
            ],
            query_size=len(request.genes),
            organism=request.organism,
        )
    except httpx.HTTPStatusError as e:
        logger.error(f"g:Profiler API error: {e}", exc_info=True)
        raise HTTPException(status_code=502, detail=f"g:Profiler API error: {str(e)}")
    except httpx.RequestError as e:
        logger.error(f"g:Profiler connection error: {e}", exc_info=True)
        raise HTTPException(status_code=502, detail=f"g:Profiler unreachable: {str(e)}")
    except Exception as e:
        logger.error(f"Enrichment analysis failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Enrichment failed: {str(e)}")
