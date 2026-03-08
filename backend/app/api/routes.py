"""
API routes for GEO Survival Analysis
"""

import asyncio
import io
import json
import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.request_models import AnalysisRequest
from app.models.response_models import AnalysisResponse, HealthResponse, GeneSurvivalResponse, GeneDatasetResult, KMCurveData
from app.services.geo_survival_workflow_orchestrator import CrossDatasetSurvivalAnalysis
from app.services.analysis_result_service import analysis_result_service
from app.services.export_service import export_service
from app.config.database import get_db
from app.api.dependencies import get_optional_current_user, get_current_active_user

logger = logging.getLogger(__name__)

router = APIRouter()

# Global orchestrator instance (will be injected via dependency)
orchestrator = None


def set_orchestrator(orch):
    """Set the orchestrator instance"""
    global orchestrator
    orchestrator = orch


# ==================== Endpoints ====================

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint
    
    Returns:
        HealthResponse with service status
    """
    return HealthResponse(
        status="healthy",
        version="2.0.0"
    )



@router.post("/search", response_model=AnalysisResponse)
async def search_datasets(
    request: AnalysisRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_optional_current_user),
):
    """
    Search for datasets and perform survival analysis
    
    Args:
        request: AnalysisRequest containing search parameters
    
    Returns:
        AnalysisResponse with survival-associated genes
    """
    global orchestrator
    
    if orchestrator is None:
        raise HTTPException(
            status_code=500,
            detail="Orchestrator not initialized"
        )
    
    try:
        # Map "claude" to "anthropic" for internal use
        model = request.model
        if model == "claude":
            model = "anthropic"
        
        logger.info(f"Received survival analysis request: {request.query} with model: {request.model} (mapped to {model})")
        
        # Run survival analysis
        result: CrossDatasetSurvivalAnalysis = await orchestrator.analyze_query(
            query=request.query,
            max_datasets=request.max_datasets,
            organism=request.organism,
            min_occurrence=request.min_occurrence,
            model=model,
            ranking_multiplier=request.ranking_multiplier,
            cancer_genes_only=request.cancer_genes_only,
            gene_filter=request.gene_filter,
        )
        
        # Convert GeneSurvivalOccurrence objects to response models
        genes_response = []
        for gene in result.common_survival_genes:
            # Convert per-dataset results if available
            per_dataset_responses = None
            if gene.per_dataset_results:
                per_dataset_responses = []
                for ds_result in gene.per_dataset_results:
                    km_high = None
                    km_low = None
                    
                    if 'km_curve_high' in ds_result and ds_result['km_curve_high']:
                        km_data = ds_result['km_curve_high']
                        km_high = KMCurveData(
                            times=km_data['times'],
                            survival_probabilities=km_data['survival_probabilities'],
                            ci_lower=km_data.get('ci_lower'),
                            ci_upper=km_data.get('ci_upper'),
                            n_samples=km_data['n_samples'],
                            n_events=km_data['n_events']
                        )
                    
                    if 'km_curve_low' in ds_result and ds_result['km_curve_low']:
                        km_data = ds_result['km_curve_low']
                        km_low = KMCurveData(
                            times=km_data['times'],
                            survival_probabilities=km_data['survival_probabilities'],
                            ci_lower=km_data.get('ci_lower'),
                            ci_upper=km_data.get('ci_upper'),
                            n_samples=km_data['n_samples'],
                            n_events=km_data['n_events']
                        )
                    
                    per_dataset_responses.append(GeneDatasetResult(
                        dataset_id=ds_result['dataset_id'],
                        dataset_title=ds_result['dataset_title'],
                        hazard_ratio=ds_result['hazard_ratio'],
                        hazard_ratio_ci_lower=ds_result['hazard_ratio_ci_lower'],
                        hazard_ratio_ci_upper=ds_result['hazard_ratio_ci_upper'],
                        cox_p_value=ds_result['cox_p_value'],
                        log_rank_p_value=ds_result['log_rank_p_value'],
                        risk_direction=ds_result['risk_direction'],
                        n_samples=ds_result['n_samples'],
                        median_survival_high=ds_result.get('median_survival_high'),
                        median_survival_low=ds_result.get('median_survival_low'),
                        km_curve_high=km_high,
                        km_curve_low=km_low
                    ))
            
            genes_response.append(GeneSurvivalResponse(
                gene_id=gene.gene_id,
                gene_symbol=gene.gene_symbol,
                n_datasets=gene.n_datasets,
                avg_hazard_ratio=gene.avg_hazard_ratio,
                avg_cox_p_value=gene.avg_cox_p_value,
                avg_log_rank_p_value=gene.avg_log_rank_p_value,
                predominant_risk=gene.predominant_risk,
                risk_direction_consistency=gene.risk_direction_consistency,
                datasets=gene.datasets,
                per_dataset_results=per_dataset_responses
            ))
        
        response = AnalysisResponse(
            query=result.query,
            n_datasets_analyzed=result.n_datasets_analyzed,
            n_datasets_with_survival=result.n_datasets_with_survival,
            common_genes=genes_response,
            processing_time=result.processing_time,
            timestamp=result.timestamp.isoformat(),
            ranking_quality_score=result.ranking_quality_score,
            ranking_recommendations=result.ranking_recommendations
        )

        # Persist result non-blocking (F07) — failure must never break the response
        try:
            user_id = current_user.id if current_user else None
            result_id = await analysis_result_service.save_result(db, response.model_dump(), user_id=user_id)
            response.result_id = result_id
        except Exception as save_err:
            logger.warning(f"Failed to persist analysis result (non-fatal): {save_err}")

        return response

    except Exception as e:
        logger.error(f"Survival analysis failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Survival analysis failed: {str(e)}"
        )


def _build_analysis_response(result: CrossDatasetSurvivalAnalysis) -> AnalysisResponse:
    """Convert a CrossDatasetSurvivalAnalysis into the API response model."""
    genes_response = []
    for gene in result.common_survival_genes:
        per_dataset_responses = None
        if gene.per_dataset_results:
            per_dataset_responses = []
            for ds_result in gene.per_dataset_results:
                km_high = None
                km_low = None

                if 'km_curve_high' in ds_result and ds_result['km_curve_high']:
                    km_data = ds_result['km_curve_high']
                    km_high = KMCurveData(
                        times=km_data['times'],
                        survival_probabilities=km_data['survival_probabilities'],
                        ci_lower=km_data.get('ci_lower'),
                        ci_upper=km_data.get('ci_upper'),
                        n_samples=km_data['n_samples'],
                        n_events=km_data['n_events']
                    )

                if 'km_curve_low' in ds_result and ds_result['km_curve_low']:
                    km_data = ds_result['km_curve_low']
                    km_low = KMCurveData(
                        times=km_data['times'],
                        survival_probabilities=km_data['survival_probabilities'],
                        ci_lower=km_data.get('ci_lower'),
                        ci_upper=km_data.get('ci_upper'),
                        n_samples=km_data['n_samples'],
                        n_events=km_data['n_events']
                    )

                per_dataset_responses.append(GeneDatasetResult(
                    dataset_id=ds_result['dataset_id'],
                    dataset_title=ds_result['dataset_title'],
                    hazard_ratio=ds_result['hazard_ratio'],
                    hazard_ratio_ci_lower=ds_result['hazard_ratio_ci_lower'],
                    hazard_ratio_ci_upper=ds_result['hazard_ratio_ci_upper'],
                    cox_p_value=ds_result['cox_p_value'],
                    log_rank_p_value=ds_result['log_rank_p_value'],
                    risk_direction=ds_result['risk_direction'],
                    n_samples=ds_result['n_samples'],
                    median_survival_high=ds_result.get('median_survival_high'),
                    median_survival_low=ds_result.get('median_survival_low'),
                    km_curve_high=km_high,
                    km_curve_low=km_low
                ))

        genes_response.append(GeneSurvivalResponse(
            gene_id=gene.gene_id,
            gene_symbol=gene.gene_symbol,
            n_datasets=gene.n_datasets,
            avg_hazard_ratio=gene.avg_hazard_ratio,
            avg_cox_p_value=gene.avg_cox_p_value,
            avg_log_rank_p_value=gene.avg_log_rank_p_value,
            predominant_risk=gene.predominant_risk,
            risk_direction_consistency=gene.risk_direction_consistency,
            datasets=gene.datasets,
            per_dataset_results=per_dataset_responses
        ))

    return AnalysisResponse(
        query=result.query,
        n_datasets_analyzed=result.n_datasets_analyzed,
        n_datasets_with_survival=result.n_datasets_with_survival,
        common_genes=genes_response,
        processing_time=result.processing_time,
        timestamp=result.timestamp.isoformat(),
        ranking_quality_score=result.ranking_quality_score,
        ranking_recommendations=result.ranking_recommendations
    )


@router.get("/search/stream")
async def stream_analysis(
    query: str = Query(..., min_length=1, max_length=500),
    max_datasets: int = Query(default=10, ge=1, le=1000),
    organism: Optional[str] = Query(default=None),
    min_occurrence: int = Query(default=2, ge=1, le=50),
    model: str = Query(default="mistral"),
    ranking_multiplier: int = Query(default=3, ge=1, le=10),
    cancer_genes_only: bool = Query(default=False),
    gene_filter: Optional[List[str]] = Query(default=None),
):
    """
    Stream analysis progress via Server-Sent Events (SSE).

    Each event is a JSON object with a ``stage`` field:
    - Progress events: ``stage``, ``message``, ``current``, ``total``
    - Final result event: ``stage == "result"``, ``result`` (full AnalysisResponse dict)
    - Error event: ``stage == "error"``, ``message``
    """
    global orchestrator

    if orchestrator is None:
        raise HTTPException(status_code=500, detail="Orchestrator not initialized")

    # Map "claude" to "anthropic" for internal use
    use_model = "anthropic" if model == "claude" else model

    parsed_gene_filter: Optional[List[str]] = (
        [g.strip().upper() for g in gene_filter if g.strip()] if gene_filter else None
    ) or None

    queue: asyncio.Queue = asyncio.Queue()

    async def progress_cb(stage: str, message: str, current: Optional[int], total: Optional[int]) -> None:
        event_data = json.dumps({"stage": stage, "message": message, "current": current, "total": total})
        await queue.put(f"data: {event_data}\n\n")

    async def run_analysis() -> None:
        try:
            result: CrossDatasetSurvivalAnalysis = await orchestrator.analyze_query(
                query=query,
                max_datasets=max_datasets,
                organism=organism,
                min_occurrence=min_occurrence,
                model=use_model,
                ranking_multiplier=ranking_multiplier,
                cancer_genes_only=cancer_genes_only,
                gene_filter=parsed_gene_filter,
                progress_callback=progress_cb,
            )
            response_obj = _build_analysis_response(result)
            result_data = json.dumps({"stage": "result", "result": response_obj.model_dump()})
            await queue.put(f"data: {result_data}\n\n")
        except Exception as e:
            logger.error(f"SSE analysis failed: {e}", exc_info=True)
            error_data = json.dumps({"stage": "error", "message": str(e)})
            await queue.put(f"data: {error_data}\n\n")
        finally:
            await queue.put(None)  # sentinel

    async def event_generator():
        asyncio.create_task(run_analysis())
        while True:
            item = await queue.get()
            if item is None:
                break
            yield item

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )


# ==================== Analysis Result Endpoints (F07) ====================

@router.get("/results/{result_id}")
async def get_analysis_result(
    result_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve a saved analysis result by ID.
    Public endpoint — no auth required (supports shareable links, F09).
    """
    result = await analysis_result_service.get_result(db, result_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Analysis result not found")
    return result


@router.get("/results/{result_id}/export")
async def export_analysis_result(
    result_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    """
    Download a publication-ready ZIP package for an analysis result.
    Includes genes.csv, per_dataset_results.csv, methods.txt, analysis_params.json.
    """
    result = await analysis_result_service.get_result(db, result_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Analysis result not found")

    zip_bytes = export_service.build_export_zip(result)
    safe_query = "".join(
        c if c.isalnum() or c in "-_" else "_"
        for c in result.get("query", "analysis")[:30]
    )
    filename = f"geo_survival_{safe_query}.zip"

    return StreamingResponse(
        io.BytesIO(zip_bytes),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/results")
async def list_analysis_results(
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    """
    List saved analysis results for the authenticated user (most recent first).
    Used by the Analysis History dashboard (F12).
    """
    results = await analysis_result_service.list_user_results(db, current_user.id, limit=limit, offset=offset)
    return {"results": results, "limit": limit, "offset": offset}
