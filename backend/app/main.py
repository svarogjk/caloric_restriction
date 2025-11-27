"""
FastAPI application for GEO Analysis Workflow
Provides REST API endpoints for GEO data analysis
"""

import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.services.geo_workflow_orchestrator import GEOWorkflowOrchestrator
from app.api import routes
from app.config.logging_config import setup_logging, get_logger

# Setup logging to console and file
setup_logging(level=logging.DEBUG)
logger = get_logger(__name__)

# Global orchestrator instance
orchestrator: Optional[GEOWorkflowOrchestrator] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifespan - initialize and cleanup services
    """
    global orchestrator
    logger.info("Starting GEO Analysis API...")
    
    orchestrator = GEOWorkflowOrchestrator(
        email="svarogjk1989@gmail.com",
        model="mistral"
    )
    
    # Set orchestrator in routes module
    routes.set_orchestrator(orchestrator)
    
    yield
    
    logger.info("Shutting down GEO Analysis API...")
    await orchestrator.close()


# Create FastAPI app
app = FastAPI(
    title="GEO Analysis API",
    description="REST API for Gene Expression Omnibus (GEO) analysis workflow",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(routes.router, prefix="/api")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
