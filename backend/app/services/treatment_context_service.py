"""Treatment Context Service (F24).

Answers: "In GEO cohorts where patients received [treatment], how did patients
with this expression profile fare?"

This powers ADVISORY treatment context: outcomes in cohorts that received a given
treatment, surfaced as options to consider/discuss — not a prescription and not a
prediction that the patient will respond. The service builds one SignatureService
model per (cancer_type, treatment) pair from GEO datasets whose search query
includes the treatment name.  Model IDs are stable (`treatment_{cancer}_{slug}`)
so they survive restarts.

Build lifecycle
--------------
1. Request arrives → for each treatment entry:
   a. Model already on disk → score patient → return result.
   b. Model not on disk but a cached analysis exists → background build.
   c. Neither → return is_building=True so the UI can request /warm explicitly.
2. POST /warm → runs the full orchestrator pipeline for missing treatment models;
   each takes ~2-5 min per query.

Patient expression is never persisted (same policy as /predict).
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Optional

from app.models.signature_models import (
    TREATMENT_RUO_DISCLAIMER,
    TreatmentComparison,
    TreatmentComparisonResult,
)

if TYPE_CHECKING:
    from app.services.signature_service import SignatureService
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Curated treatment queries per cancer type
# ---------------------------------------------------------------------------

TREATMENT_QUERIES: dict[str, list[dict[str, str]]] = {
    "breast": [
        {
            "name": "Adjuvant chemotherapy",
            "slug": "chemo",
            "query": "breast cancer adjuvant chemotherapy overall survival",
        },
        {
            "name": "Hormone therapy (tamoxifen / AI)",
            "slug": "hormone",
            "query": "breast cancer tamoxifen aromatase inhibitor overall survival",
        },
        {
            "name": "Neoadjuvant chemotherapy",
            "slug": "neoadjuvant",
            "query": "breast cancer neoadjuvant chemotherapy overall survival",
        },
    ],
    "lung": [
        {
            "name": "Platinum-based chemotherapy",
            "slug": "platinum",
            "query": "lung adenocarcinoma platinum chemotherapy overall survival",
        },
        {
            "name": "EGFR TKI (gefitinib / erlotinib)",
            "slug": "egfr_tki",
            "query": "lung cancer EGFR TKI gefitinib erlotinib overall survival",
        },
        {
            "name": "Immunotherapy (PD-1 / PD-L1)",
            "slug": "immuno",
            "query": "lung cancer immunotherapy PD-L1 pembrolizumab overall survival",
        },
    ],
    "colorectal": [
        {
            "name": "FOLFOX / oxaliplatin",
            "slug": "folfox",
            "query": "colorectal cancer FOLFOX oxaliplatin chemotherapy overall survival",
        },
        {
            "name": "Anti-VEGF (bevacizumab)",
            "slug": "anti_vegf",
            "query": "colorectal cancer bevacizumab VEGF overall survival",
        },
        {
            "name": "Anti-EGFR (cetuximab)",
            "slug": "anti_egfr",
            "query": "colorectal cancer cetuximab EGFR overall survival",
        },
    ],
    "ovarian": [
        {
            "name": "Platinum + taxane",
            "slug": "plat_taxane",
            "query": "ovarian cancer platinum taxane paclitaxel overall survival",
        },
        {
            "name": "Bevacizumab maintenance",
            "slug": "beva",
            "query": "ovarian cancer bevacizumab maintenance overall survival",
        },
    ],
    "gastric": [
        {
            "name": "Platinum-based chemotherapy",
            "slug": "platinum",
            "query": "gastric cancer platinum chemotherapy overall survival",
        },
        {
            "name": "Trastuzumab (HER2+)",
            "slug": "trastuzumab",
            "query": "gastric cancer trastuzumab HER2 overall survival",
        },
    ],
    "glioma": [
        {
            "name": "Temozolomide + radiotherapy",
            "slug": "tmz_rt",
            "query": "glioblastoma temozolomide radiotherapy overall survival",
        },
        {
            "name": "Bevacizumab",
            "slug": "beva",
            "query": "glioblastoma bevacizumab overall survival",
        },
    ],
}


def _model_id(cancer_type: str, slug: str) -> str:
    return f"treatment_{cancer_type}_{slug}"


class TreatmentContextService:
    """Builds and caches treatment-specific prognostic models; scores patients."""

    def __init__(self, signature_service: "SignatureService") -> None:
        self._sig = signature_service
        self._building: set[str] = set()  # model_ids currently being built

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def supported_cancer_types(self) -> list[str]:
        return list(TREATMENT_QUERIES.keys())

    async def get_treatment_comparison(
        self,
        cancer_type: str,
        expression: dict[str, float],
        clinical: Optional[dict[str, float | str]],
        db: "AsyncSession",
    ) -> TreatmentComparisonResult:
        entries = TREATMENT_QUERIES.get(cancer_type.lower(), [])
        comparisons: list[TreatmentComparison] = []

        for entry in entries:
            comparison = await self._get_or_build_treatment(
                cancer_type=cancer_type.lower(),
                entry=entry,
                expression=expression,
                clinical=clinical,
                db=db,
            )
            comparisons.append(comparison)

        return TreatmentComparisonResult(cancer_type=cancer_type, treatments=comparisons)

    async def warm(self, cancer_type: str, db: "AsyncSession") -> list[str]:
        """Trigger background builds for all treatment models of a cancer type.
        Returns the list of slugs queued."""
        entries = TREATMENT_QUERIES.get(cancer_type.lower(), [])
        queued: list[str] = []
        for entry in entries:
            mid = _model_id(cancer_type, entry["slug"])
            if self._sig.get_model(mid) is not None:
                continue
            if mid in self._building:
                continue
            asyncio.create_task(
                self._build_treatment_model(cancer_type.lower(), entry, db),
                name=f"treatment_build_{mid}",
            )
            queued.append(entry["slug"])
        return queued

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _get_or_build_treatment(
        self,
        cancer_type: str,
        entry: dict[str, str],
        expression: dict[str, float],
        clinical: Optional[dict[str, float | str]],
        db: "AsyncSession",
    ) -> TreatmentComparison:
        mid = _model_id(cancer_type, entry["slug"])

        # Model already available → score immediately.
        model = self._sig.get_model(mid)
        if model is not None:
            try:
                result = self._sig.score_single_sample(model, expression, clinical)
                return TreatmentComparison(
                    name=entry["name"],
                    slug=entry["slug"],
                    risk_group=result.risk_group,
                    risk_percentile=result.risk_percentile,
                    reference_km=model.reference_km,
                    predicted_survival=result.predicted_survival,
                    n_cohorts=len(model.cohort_validations) + 1,
                    n_patients=model.n_training_samples,
                    pooled_c_index=model.pooled_c_index,
                    is_building=False,
                )
            except (ValueError, KeyError, RuntimeError) as exc:
                logger.warning("Score failed for %s: %s", mid, exc)
                return TreatmentComparison(
                    name=entry["name"], slug=entry["slug"],
                    is_building=False, build_error=str(exc),
                )

        # Model not on disk yet — kick off a background build if not already running.
        if mid not in self._building:
            asyncio.create_task(
                self._build_treatment_model(cancer_type, entry, db),
                name=f"treatment_build_{mid}",
            )

        return TreatmentComparison(
            name=entry["name"], slug=entry["slug"], is_building=True,
        )

    async def _build_treatment_model(
        self, cancer_type: str, entry: dict[str, str], db: "AsyncSession"
    ) -> None:
        """Background: build a treatment-specific signature model and persist it."""
        from app.services.analysis_result_service import analysis_result_service

        mid = _model_id(cancer_type, entry["slug"])
        if mid in self._building:
            return
        self._building.add(mid)
        logger.info("Treatment model build started: %s (%s)", mid, entry["query"])

        try:
            # Try to find a cached GEO analysis matching this query first.
            cached = await analysis_result_service.find_recent_by_query(db, entry["query"])
            if cached and cached.get("result_id"):
                full = await analysis_result_service.get_result(db, cached["result_id"])
                if full:
                    model = await self._sig.build_from_result(full, cancer_type=cancer_type)
                    model.model_id = mid
                    self._sig.save_model_to_disk(model)
                    logger.info("Treatment model built from cache: %s", mid)
                    return

            # No cached analysis — run the full pipeline via the orchestrator.
            if self._sig.orchestrator is None:
                logger.warning("Orchestrator unavailable, cannot build %s", mid)
                return

            from app.api.routes import _build_analysis_response

            raw = await self._sig.orchestrator.analyze_query(
                query=entry["query"],
                max_datasets=10,
                min_occurrence=2,
            )
            result_dict = _build_analysis_response(raw).model_dump()
            model = await self._sig.build_from_result(result_dict, cancer_type=cancer_type)
            model.model_id = mid
            self._sig.save_model_to_disk(model)
            logger.info("Treatment model built from fresh analysis: %s", mid)

        except (ValueError, KeyError, OSError, RuntimeError) as exc:
            logger.warning("Treatment model build failed for %s: %s", mid, exc)
        finally:
            self._building.discard(mid)


# Module-level singleton — wired in main.py
_service: Optional[TreatmentContextService] = None


def set_treatment_service(sig: "SignatureService") -> None:
    global _service
    _service = TreatmentContextService(sig)


def get_treatment_service() -> TreatmentContextService:
    if _service is None:
        raise RuntimeError("TreatmentContextService not initialised")
    return _service
