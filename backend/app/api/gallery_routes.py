"""
Oncologist Mode gallery (F20).

Serves a curated catalogue of common cancer types with ready-to-run prognostic
queries. Each entry is enriched with a `result_id` when a matching pre-run
analysis already exists in the database, so the oncologist can load results
instantly instead of waiting for a fresh run.

Reuses results-persistence (analysis_result_service) — no new storage.
"""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_db
from app.services.analysis_result_service import analysis_result_service

logger = logging.getLogger(__name__)

router = APIRouter()

# Curated catalogue. Queries are phrased the way the analysis pipeline expects
# (cancer type + "overall survival"). Kept small and high-signal.
CURATED_CANCERS = [
    {
        "key": "breast",
        "label": "Breast cancer",
        "query": "breast cancer overall survival",
        "blurb": "ER/HER2-spanning cohorts; strong prognostic expression signal.",
        "icon": "🎀",
    },
    {
        "key": "lung",
        "label": "Lung adenocarcinoma",
        "query": "lung adenocarcinoma overall survival",
        "blurb": "NSCLC cohorts across stages; classic prognostic biomarker target.",
        "icon": "🫁",
    },
    {
        "key": "colorectal",
        "label": "Colorectal cancer",
        "query": "colorectal cancer overall survival",
        "blurb": "Colon/rectal adenocarcinoma; MSI and stage heterogeneity.",
        "icon": "🧬",
    },
    {
        "key": "ovarian",
        "label": "Ovarian cancer",
        "query": "ovarian cancer overall survival",
        "blurb": "High-grade serous cohorts; aggressive, prognosis-driven.",
        "icon": "🎗️",
    },
    {
        "key": "gastric",
        "label": "Gastric cancer",
        "query": "gastric cancer overall survival",
        "blurb": "Stomach adenocarcinoma; molecularly diverse cohorts.",
        "icon": "🩺",
    },
    {
        "key": "glioma",
        "label": "Glioma / GBM",
        "query": "glioma overall survival",
        "blurb": "Brain tumours; well-characterised prognostic expression markers.",
        "icon": "🧠",
    },
]


@router.get("/gallery")
async def get_gallery(db: AsyncSession = Depends(get_db)):
    """Return the curated cancer-type catalogue, each enriched with a cached
    result_id when a matching pre-run analysis exists."""
    items = []
    for entry in CURATED_CANCERS:
        cached = None
        try:
            cached = await analysis_result_service.find_recent_by_query(db, entry["query"])
        except (OSError, RuntimeError) as e:
            logger.warning("Gallery lookup failed for %s: %s", entry["key"], e)
        items.append(
            {
                **entry,
                "result_id": cached["result_id"] if cached else None,
                "n_genes_found": cached["n_genes_found"] if cached else None,
                "n_datasets_with_survival": cached["n_datasets_with_survival"] if cached else None,
                "cached_at": cached["created_at"] if cached else None,
            }
        )
    return {"cancers": items}
