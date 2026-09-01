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
from app.services.signature_service import SignatureService, covariate_form_spec

logger = logging.getLogger(__name__)

router = APIRouter()

# Injected at startup (shared with the signature/predict routes).
signature_service: SignatureService | None = None


def set_signature_service(svc: SignatureService) -> None:
    global signature_service
    signature_service = svc

# Curated catalogue. Queries are phrased the way the analysis pipeline expects
# (cancer type + "overall survival"). Kept small and high-signal.
CURATED_CANCERS = [
    {
        "key": "breast",
        "label": "Breast cancer",
        "query": "breast cancer overall survival",
        "blurb": "ER/HER2-spanning cohorts; strong predictive expression signal.",
        "icon": "🎀",
    },
    {
        "key": "lung",
        "label": "Lung adenocarcinoma",
        "query": "lung adenocarcinoma overall survival",
        "blurb": "NSCLC cohorts across stages; classic predictive biomarker target.",
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
        "blurb": "High-grade serous cohorts; aggressive, outcome-driven.",
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
        "blurb": "Brain tumours; well-characterised predictive expression markers.",
        "icon": "🧠",
    },
]


@router.get("/gallery")
async def get_gallery(db: AsyncSession = Depends(get_db)):
    """Return the curated cancer-type catalogue. Each entry is enriched with the
    durable prognostic model used to score a patient (model_id, discrimination,
    and the clinical-covariate form spec), plus any cached cohort-analysis id."""
    items = []
    for entry in CURATED_CANCERS:
        cached = None
        try:
            cached = await analysis_result_service.find_recent_by_query(db, entry["query"])
        except (OSError, RuntimeError) as e:
            logger.warning("Gallery lookup failed for %s: %s", entry["key"], e)

        model = signature_service.find_model_by_cancer(entry["key"]) if signature_service else None

        items.append(
            {
                **entry,
                # Patient-scoring model (the headline of Oncologist Mode):
                "model_id": model.model_id if model else None,
                "n_genes": len(model.genes) if model else None,
                "pooled_c_index": model.pooled_c_index if model else None,
                "c_index_expression_only": model.c_index_expression_only if model else None,
                "c_index_combined": model.c_index_combined if model else None,
                "delta_c_index": model.delta_c_index if model else None,
                "clinical_covariates": covariate_form_spec(model) if model else [],
                "model_is_demo": model.is_demo if model else None,
                # Underlying cohort analysis (kept for provenance / linking):
                "result_id": cached["result_id"] if cached else None,
                "n_genes_found": cached["n_genes_found"] if cached else None,
                "n_datasets_with_survival": cached["n_datasets_with_survival"] if cached else None,
                "cached_at": cached["created_at"] if cached else None,
            }
        )

    # Single source of truth for the frontend's live expression-feedback
    # thresholds (utils/expressionFeedback.ts), so the UI can never drift
    # from the actual scoring behaviour in SignatureService.
    scoring_thresholds = {
        "qn_min_genes": SignatureService._QN_MIN_GENES,
        "low_coverage_frac": SignatureService._LOW_COVERAGE_FRAC,
    }
    return {"cancers": items, "scoring_thresholds": scoring_thresholds}
