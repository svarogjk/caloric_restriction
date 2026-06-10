"""
FastAPI application for GEO Survival Analysis Workflow
Provides REST API endpoints for survival analysis on GEO data
"""

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.services.geo_survival_workflow_orchestrator import GEOSurvivalWorkflowOrchestrator
from app.services.chat.dataset_rag_service import DatasetRAGService
from app.services.chat.geo_preview_service import GEOPreviewService
from app.services.chat.agent_tools import AgentDeps
from app.api import routes, chat_routes, auth_routes
from app.api.enrichment_routes import router as enrichment_router
from app.api.compare_routes import router as compare_router
from app.api import signature_routes, gallery_routes
from app.api.gallery_routes import router as gallery_router
from app.services.signature_service import SignatureService
from app.services.curated_models import ensure_curated_models
from app.services.therapy_evidence_service import TherapyEvidenceService
from app.config.logging_config import setup_logging, get_logger
from app.config.database import init_db, close_db, get_db_session
from app.config.settings import settings
from app.utils.memory_tracker import log_memory_checkpoint

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
        api_key=settings.ncbi_api_key or None,
        email=settings.email,
        model="mistral"
    )
    routes.set_orchestrator(orchestrator)

    # Initialize prognostic signature service (F17/F18/F19/F23) — shares orchestrator
    signature_service = SignatureService(orchestrator=orchestrator)
    signature_routes.set_signature_service(signature_service)
    gallery_routes.set_signature_service(signature_service)
    # Load durable curated models, then ensure each curated cancer has one
    # (real build when cohorts are cached, else a synthetic demo model).
    signature_service.load_persisted_models()
    try:
        async with get_db_session() as db:
            built = await ensure_curated_models(signature_service, db)
        logger.info("Curated prognostic models ready: %s", ", ".join(built))
    except (OSError, RuntimeError, ValueError) as exc:
        logger.warning("Curated model preparation skipped: %s", exc)

    # Bundled CIViC/DGIdb evidence for the grounded therapy-rationale endpoint.
    therapy_evidence_service = TherapyEvidenceService()
    therapy_evidence_service.load()
    chat_routes.set_therapy_services(signature_service, therapy_evidence_service)

    # Initialize RAG service and index local datasets into in-memory store
    rag_service = DatasetRAGService.from_env()
    try:
        n_indexed = await rag_service.index_datasets()
        logger.info(f"RAG index ready ({n_indexed} new documents embedded)")
    except (ConnectionError, RuntimeError) as exc:
        logger.warning(f"RAG indexing skipped (DB may be offline): {exc}")

    # Inject service dependencies into the PydanticAI agent
    geo_preview_service = GEOPreviewService()
    estimation_service = chat_routes.get_estimation_service()
    deps = AgentDeps(
        rag_service=rag_service,
        estimation_service=estimation_service,
        geo_preview_service=geo_preview_service,
    )
    chat_routes.set_deps(deps)

    log_memory_checkpoint("startup_complete")

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
_cors_origin = os.getenv("CORS_ORIGIN", "http://localhost:5173")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[_cors_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(routes.router, prefix="/api")
app.include_router(chat_routes.router, prefix="/api")
app.include_router(auth_routes.router, prefix="/api")
app.include_router(enrichment_router, prefix="/api")
app.include_router(compare_router, prefix="/api")
app.include_router(signature_routes.router, prefix="/api")
app.include_router(gallery_router, prefix="/api")

# Serve compiled React frontend (present in Docker image, absent in dev)
_DIST = Path("frontend/dist")
if _DIST.exists():
    app.mount("/assets", StaticFiles(directory=_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str) -> FileResponse:  # noqa: ARG001
        return FileResponse(_DIST / "index.html")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
