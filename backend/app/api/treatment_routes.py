"""Treatment Context API (F24).

POST /api/treatment-context        — score patient against treatment-specific models
POST /api/treatment-context/warm   — pre-build treatment models for a cancer type
GET  /api/treatment-context/types  — list supported cancer types and their treatments
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_db_session
from app.models.signature_models import TreatmentComparisonResult, TreatmentContextRequest
from app.services.treatment_context_service import (
    TREATMENT_QUERIES,
    get_treatment_service,
)

router = APIRouter(tags=["treatment-context"])


class WarmRequest(BaseModel):
    cancer_type: str
    cancer_genes_only: bool = False


class WarmResponse(BaseModel):
    cancer_type: str
    queued: list[str]
    already_built: list[str]


class SupportedTypesResponse(BaseModel):
    cancer_types: dict[str, list[dict[str, str]]]


@router.post("/treatment-context", response_model=TreatmentComparisonResult)
async def get_treatment_context(
    request: TreatmentContextRequest,
    db: AsyncSession = Depends(get_db_session),
) -> TreatmentComparisonResult:
    """Score a patient's expression against treatment-specific prognostic models.

    Returns per-treatment risk groups and KM curves from GEO cohorts where
    that treatment was documented.  Models build in the background on first
    call; poll until `is_building` is False for all treatments.
    """
    cancer_type = request.cancer_type.lower()
    if cancer_type not in TREATMENT_QUERIES:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported cancer type '{cancer_type}'. "
                   f"Supported: {', '.join(TREATMENT_QUERIES)}",
        )
    if len(request.expression) < 10:
        raise HTTPException(
            status_code=422,
            detail="At least 10 gene expression values are required.",
        )

    service = get_treatment_service()
    return await service.get_treatment_comparison(
        cancer_type=cancer_type,
        expression=request.expression,
        clinical=request.clinical,
        db=db,
        cancer_genes_only=request.cancer_genes_only,
    )


@router.post("/treatment-context/warm", response_model=WarmResponse)
async def warm_treatment_models(
    request: WarmRequest,
    db: AsyncSession = Depends(get_db_session),
) -> WarmResponse:
    """Trigger background builds for all treatment models of a cancer type.

    Call this proactively (e.g. when the user picks a cancer type in Oncologist
    Mode) so models are ready by the time the patient is scored.
    """
    cancer_type = request.cancer_type.lower()
    if cancer_type not in TREATMENT_QUERIES:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported cancer type '{cancer_type}'.",
        )

    service = get_treatment_service()
    queued = await service.warm(cancer_type, db, cancer_genes_only=request.cancer_genes_only)
    entries = TREATMENT_QUERIES[cancer_type]
    all_slugs = {e["slug"] for e in entries}
    already_built = sorted(all_slugs - set(queued))
    return WarmResponse(cancer_type=cancer_type, queued=queued, already_built=already_built)


@router.get("/treatment-context/types", response_model=SupportedTypesResponse)
async def list_supported_types() -> SupportedTypesResponse:
    """Return the supported cancer types and their curated treatment entries."""
    simplified = {
        ct: [{"name": e["name"], "slug": e["slug"]} for e in entries]
        for ct, entries in TREATMENT_QUERIES.items()
    }
    return SupportedTypesResponse(cancer_types=simplified)
