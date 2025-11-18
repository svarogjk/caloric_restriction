"""
API routes for GEO Analysis
"""

import logging
from fastapi import APIRouter, HTTPException

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
    Search for datasets related to a query using LLM analysis
    
    Args:
        request: AnalysisRequest containing search parameters
    
    Returns:
        AnalysisResponse with common genes and analysis results
    """
    global orchestrator
    
    if orchestrator is None:
        raise HTTPException(
            status_code=500,
            detail="Orchestrator not initialized"
        )
    
    try:
        logger.info(f"Received search request: {request.query}")
        
        # Run analysis with the search query
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
        logger.error(f"Search failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )

