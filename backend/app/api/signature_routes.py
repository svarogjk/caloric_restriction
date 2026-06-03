"""
API routes for the prognostic signature (F17) and single-sample scoring (F23).

Positioning: prognostic, research-use-only. Patient expression submitted to
/predict is held in memory only — never persisted, never logged.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.signature_models import (
    PredictRequest,
    PredictResponse,
    PrognosticModel,
    SignatureRequest,
)
from app.services.signature_service import SignatureService
from app.services.analysis_result_service import analysis_result_service
from app.config.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter()

# Injected at startup (shares the orchestrator with the analysis routes).
signature_service: SignatureService | None = None


def set_signature_service(svc: SignatureService) -> None:
    global signature_service
    signature_service = svc


@router.post("/signature", response_model=PrognosticModel)
async def build_signature(
    request: SignatureRequest,
    db: AsyncSession = Depends(get_db),
):
    """Build a validated multi-gene prognostic signature (F17).

    Either pass `demo: true` (deterministic synthetic data, no GEO needed) or a
    `result_id` from a saved analysis to derive candidate genes + cohorts.
    """
    if signature_service is None:
        raise HTTPException(status_code=500, detail="Signature service not initialized")

    if request.demo:
        try:
            return signature_service.build_demo_signature(max_genes=min(request.max_genes, 12))
        except (ValueError, RuntimeError) as e:
            logger.error("Demo signature build failed: %s", e, exc_info=True)
            raise HTTPException(status_code=500, detail=f"Demo signature failed: {e}")

    if not request.result_id:
        raise HTTPException(
            status_code=400,
            detail="Provide a result_id (or set demo=true).",
        )

    result = await analysis_result_service.get_result(db, request.result_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Analysis result not found")

    try:
        return await signature_service.build_from_result(result, max_genes=request.max_genes)
    except ValueError as e:
        # Expected, user-actionable failures (no cached cohorts, too few genes).
        logger.warning("Signature build rejected: %s", e)
        raise HTTPException(status_code=422, detail=str(e))
    except (OSError, KeyError) as e:
        logger.error("Signature build failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Signature build failed")


@router.get("/signature/{model_id}", response_model=PrognosticModel)
async def get_signature(model_id: str):
    """Fetch a previously built model (used by F18 nomogram / F19 benchmark UIs)."""
    if signature_service is None:
        raise HTTPException(status_code=500, detail="Signature service not initialized")
    model = signature_service.get_model(model_id)
    if model is None:
        raise HTTPException(status_code=404, detail="Model not found (may have been evicted)")
    return model


@router.get("/signature/{model_id}/demo-patient")
async def get_demo_patient(model_id: str):
    """Return a built-in demo patient expression profile for the F23 flow."""
    if signature_service is None:
        raise HTTPException(status_code=500, detail="Signature service not initialized")
    model = signature_service.get_model(model_id)
    if model is None:
        raise HTTPException(status_code=404, detail="Model not found")
    return {"model_id": model_id, "expression": signature_service.build_demo_patient(model)}


@router.post("/predict", response_model=PredictResponse)
async def predict_single_sample(request: PredictRequest):
    """Score a single tumour sample against a locked model (F23).

    Research use only. The submitted expression profile is used in-memory to
    compute a score and is neither stored nor logged.
    """
    if signature_service is None:
        raise HTTPException(status_code=500, detail="Signature service not initialized")
    model = signature_service.get_model(request.model_id)
    if model is None:
        raise HTTPException(status_code=404, detail="Model not found (may have been evicted)")
    if not request.expression:
        raise HTTPException(status_code=400, detail="Empty expression profile")
    try:
        return signature_service.score_single_sample(model, request.expression)
    except (ValueError, KeyError) as e:
        logger.warning("Single-sample scoring failed: %s", e)
        raise HTTPException(status_code=422, detail=str(e))
