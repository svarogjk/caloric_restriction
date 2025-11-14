"""
API routes for GEO Analysis
"""

import logging
from fastapi import APIRouter, HTTPException, BackgroundTasks

from app.models.request_models import AnalysisRequest
from app.models.response_models import AnalysisResponse, HealthResponse, GeneOccurrenceResponse
from app.services.geo_workflow_orchestrator import CrossDatasetAnalysis

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
        version="1.0.0"
    )


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_geo_data(request: AnalysisRequest):
    """
    Analyze GEO datasets for common differential expression patterns
    
    Args:
        request: AnalysisRequest containing search parameters
    
    Returns:
        AnalysisResponse with common genes and analysis results
    
    Raises:
        HTTPException: If analysis fails
    """
    global orchestrator
    
    if orchestrator is None:
        raise HTTPException(
            status_code=500,
            detail="Orchestrator not initialized"
        )
    
    try:
        logger.info(f"Received analysis request: {request.query}")
        
        # Run analysis
        result: CrossDatasetAnalysis = await orchestrator.analyze_query(
            query=request.query,
            max_datasets=request.max_datasets,
            organism=request.organism,
            min_occurrence=request.min_occurrence
        )
        
        # Convert GeneOccurrence objects to response models
        genes_response = [
            GeneOccurrenceResponse(
                gene_id=gene.gene_id,
                n_datasets=gene.n_datasets,
                avg_log_fc=gene.avg_log_fc,
                direction_consistency=gene.direction_consistency,
                datasets=gene.datasets
            )
            for gene in result.common_genes
        ]
        
        return AnalysisResponse(
            query=result.query,
            n_datasets_analyzed=result.n_datasets_analyzed,
            n_datasets_with_degs=result.n_datasets_with_degs,
            common_genes=genes_response,
            processing_time=result.processing_time,
            timestamp=result.timestamp.isoformat()
        )
    
    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )


@router.get("/analyze/quick", response_model=AnalysisResponse)
async def quick_analysis():
    """
    Quick analysis endpoint with default parameters
    
    Useful for testing the API
    
    Returns:
        AnalysisResponse with common genes
    """
    request = AnalysisRequest(
        query="caloric restriction aging lifespan",
        max_datasets=5,
        organism="Mus musculus",
        min_occurrence=2
    )
    return await analyze_geo_data(request)


@router.post("/analyze/async")
async def analyze_geo_data_async(
    request: AnalysisRequest,
    background_tasks: BackgroundTasks
):
    """
    Asynchronous analysis endpoint - returns immediately with task ID
    
    Note: This is a placeholder for future implementation of
    job tracking and result retrieval
    
    Args:
        request: AnalysisRequest containing search parameters
        background_tasks: FastAPI background tasks
    
    Returns:
        Dict with task_id for result retrieval
    """
    # TODO: Implement job tracking with database
    return {
        "message": "Async analysis not yet implemented",
        "status": "not_implemented"
    }
