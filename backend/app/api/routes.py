"""
API routes for GEO Analysis
"""

import logging
from fastapi import APIRouter, HTTPException

from app.models.request_models import AnalysisRequest
from app.models.response_models import AnalysisResponse, HealthResponse, GeneOccurrenceResponse
from app.services.geo_workflow_orchestrator import CrossDatasetAnalysis
from app.services.cache_manager import CacheManager

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
        # Map "claude" to "anthropic" for internal use
        model = request.model
        if model == "claude":
            model = "anthropic"
        
        # Determine gene mapping model
        gene_mapping_model = request.gene_mapping_model
        if gene_mapping_model and gene_mapping_model == "claude":
            gene_mapping_model = "anthropic"
        elif not gene_mapping_model:
            gene_mapping_model = model  # Use main model if not specified
        
        logger.info(f"Received search request: {request.query} with model: {request.model} (mapped to {model}), "
                   f"AI gene mapping: {request.use_ai_gene_mapping}, "
                   f"gene mapping model: {request.gene_mapping_model} (mapped to {gene_mapping_model})")
        
        # Run analysis with the search query and selected model
        result: CrossDatasetAnalysis = await orchestrator.analyze_query(
            query=request.query,
            max_datasets=request.max_datasets,
            organism=request.organism,
            min_occurrence=request.min_occurrence,
            model=model,
            ranking_multiplier=request.ranking_multiplier,
            use_ai_gene_mapping=request.use_ai_gene_mapping
        )
        
        # Convert GeneOccurrence objects to response models
        genes_response = [
            GeneOccurrenceResponse(
                gene_id=gene.gene_id,
                n_datasets=gene.n_datasets,
                avg_log_fc=gene.avg_log_fc,
                avg_p_value=gene.avg_p_value,
                avg_adj_p_value=gene.avg_adj_p_value,
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


@router.get("/cache/info")
async def get_cache_info():
    """
    Get information about cached datasets for session reuse
    
    Returns:
        Dictionary with cache status and cached dataset information
    """
    return CacheManager.get_cache_info()


@router.get("/cache/platforms")
async def get_platform_cache_info():
    """
    Get information about cached platform gene mappings
    
    Returns:
        Dictionary with platform cache status
    """
    return CacheManager.get_platform_cache_info()


@router.get("/cache/speedup")
async def get_cache_speedup():
    """
    Get estimated performance improvement from cache
    
    Returns:
        Dictionary with speedup estimates
    """
    return CacheManager.estimate_analysis_speedup()


@router.delete("/cache/{dataset_id}")
async def clear_dataset_cache(dataset_id: str):
    """
    Clear cache for a specific dataset
    
    Args:
        dataset_id: GEO dataset ID (e.g., GSE272329)
    
    Returns:
        Success status
    """
    success = CacheManager.clear_dataset_cache(dataset_id)
    if success:
        return {"message": f"Cache cleared for {dataset_id}"}
    else:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear cache for {dataset_id}"
        )


@router.delete("/cache")
async def clear_all_cache():
    """
    Clear entire local cache (use with caution)
    
    Returns:
        Summary of cleared cache
    """
    result = CacheManager.clear_all_cache()
    if result.get("success"):
        return result
    else:
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Unknown error")
        )

