"""
API routes for GEO Survival Analysis
"""

import logging
from fastapi import APIRouter, HTTPException

from app.models.request_models import AnalysisRequest
from app.models.response_models import AnalysisResponse, HealthResponse, GeneSurvivalResponse, GeneDatasetResult, KMCurveData
from app.services.geo_survival_workflow_orchestrator import CrossDatasetSurvivalAnalysis

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


@router.get("/models")
async def get_available_models():
    """
    Get available LLM models for search
    
    Returns:
        List of available model names
    """
    return ["mistral", "claude"]


@router.post("/search", response_model=AnalysisResponse)
async def search_datasets(request: AnalysisRequest):
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
        
        return AnalysisResponse(
            query=result.query,
            n_datasets_analyzed=result.n_datasets_analyzed,
            n_datasets_with_survival=result.n_datasets_with_survival,
            common_genes=genes_response,
            processing_time=result.processing_time,
            timestamp=result.timestamp.isoformat()
        )
    
    except Exception as e:
        logger.error(f"Survival analysis failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Survival analysis failed: {str(e)}"
        )
