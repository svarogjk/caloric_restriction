"""
FastAPI application for GEO Survival Analysis Workflow
Provides REST API endpoints for survival analysis on GEO data
"""

import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.services.geo_survival_workflow_orchestrator import GEOSurvivalWorkflowOrchestrator
from app.api import routes, chat_routes, auth_routes
from app.config.logging_config import setup_logging, get_logger
from app.config.database import init_db, close_db
from app.config.settings import settings

# Setup logging to console and file
setup_logging(level=logging.DEBUG)
logger = get_logger(__name__)

# Global orchestrator instance
orchestrator: Optional[GEOSurvivalWorkflowOrchestrator] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifespan - initialize and cleanup services
    """
    global orchestrator
    logger.info("Starting GEO Survival Analysis API...")

    # Initialize database
    await init_db()
    logger.info("Database initialized")

    orchestrator = GEOSurvivalWorkflowOrchestrator(
        email=settings.email,
        model="mistral"
    )

    # Set orchestrator in routes module
    routes.set_orchestrator(orchestrator)

    yield

    logger.info("Shutting down GEO Survival Analysis API...")
    await orchestrator.close()
    await close_db()


# Create FastAPI app
app = FastAPI(
    title="GEO Survival Analysis API",
    description="REST API for survival analysis on Gene Expression Omnibus (GEO) data",
    version="2.0.0",
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
app.include_router(chat_routes.router, prefix="/api")
app.include_router(auth_routes.router, prefix="/api")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
