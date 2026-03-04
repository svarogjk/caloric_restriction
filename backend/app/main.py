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
from app.services.chat.dataset_rag_service import DatasetRAGService
from app.services.chat.geo_preview_service import GEOPreviewService
from app.services.chat.agent_tools import build_tools
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

    # Initialize survival analysis orchestrator
    orchestrator = GEOSurvivalWorkflowOrchestrator(
        email=settings.email,
        model="mistral"
    )
    routes.set_orchestrator(orchestrator)

    # Initialize RAG service and index local datasets into pgvector
    rag_service = DatasetRAGService.from_env()
    try:
        n_indexed = await rag_service.index_datasets()
        logger.info(f"RAG index ready ({n_indexed} new documents embedded)")
    except (ConnectionError, RuntimeError) as exc:
        logger.warning(f"RAG indexing skipped (DB may be offline): {exc}")

    # Build and inject agent tools
    geo_preview_service = GEOPreviewService()
    estimation_service = chat_routes.get_estimation_service()
    tools = build_tools(
        rag_service=rag_service,
        estimation_service=estimation_service,
        geo_preview_service=geo_preview_service,
        orchestrator=orchestrator,
    )
    chat_routes.set_tools(tools)

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
