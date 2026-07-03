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
import re
import time
from collections import OrderedDict
from typing import TYPE_CHECKING, Optional

from app.config.database import get_db_session
from app.models.signature_models import (
    COHORT_REFERENCE_CAVEAT,
    TREATMENT_RUO_DISCLAIMER,
    TreatmentComparison,
    TreatmentComparisonResult,
    TreatmentKMEvidence,
)
from app.services.survival_analysis_service import _drug_name_tokens, _normalize_drug_name

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


def _slugify_drug_name(drug_name: str) -> str:
    """Filesystem/model-id-safe slug for an arbitrary (uncurated) drug name."""
    slug = re.sub(r"[^a-z0-9]+", "_", drug_name.strip().lower()).strip("_")
    return slug or "drug"


# Negative-build results ("no matching GEO datasets") expire after this long,
# so a drug that later gains coverage isn't cached-negative forever, while
# repeated Regenerate clicks within a session don't re-trigger a fresh
# 2-5 min orchestrator run for a drug with no data.
_NEGATIVE_CACHE_TTL_SECONDS = 3600
_NEGATIVE_CACHE_MAX = 200


class TreatmentContextService:
    """Builds and caches treatment-specific prognostic models; scores patients."""

    def __init__(self, signature_service: "SignatureService") -> None:
        self._sig = signature_service
        self._building: set[str] = set()  # model_ids currently being built
        # model_id -> (reason, cached_at_monotonic) for recent failed/empty builds.
        self._negative_cache: "OrderedDict[str, tuple[str, float]]" = OrderedDict()

    def _negative_cache_get(self, mid: str) -> Optional[str]:
        entry = self._negative_cache.get(mid)
        if entry is None:
            return None
        reason, cached_at = entry
        if time.monotonic() - cached_at > _NEGATIVE_CACHE_TTL_SECONDS:
            del self._negative_cache[mid]
            return None
        self._negative_cache.move_to_end(mid)
        return reason

    def _negative_cache_put(self, mid: str, reason: str) -> None:
        self._negative_cache[mid] = (reason, time.monotonic())
        self._negative_cache.move_to_end(mid)
        if len(self._negative_cache) > _NEGATIVE_CACHE_MAX:
            self._negative_cache.popitem(last=False)

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

    async def get_or_build_km_for_drug(
        self, cancer_type: str, drug_name: str
    ) -> TreatmentKMEvidence:
        """Tier-2 cohort-reference KM evidence for a drug suggested in the
        "Treatments to consider" panel (F24b). Reuses a curated
        `TREATMENT_QUERIES` entry when the drug name matches one; otherwise
        synthesizes a query and builds/caches a dedicated treatment model the
        same way curated entries are built. A short-TTL negative-result cache
        avoids re-running a full orchestrator pipeline on every Regenerate
        click for a drug with no matching GEO datasets.
        """
        cancer_key = cancer_type.lower()
        entry = self._match_curated_entry(cancer_key, drug_name) or {
            "name": drug_name,
            "slug": _slugify_drug_name(drug_name),
            "query": f"{cancer_type} {drug_name} overall survival",
        }
        mid = _model_id(cancer_key, entry["slug"])

        neg_reason = self._negative_cache_get(mid)
        if neg_reason is not None:
            return TreatmentKMEvidence(drug=drug_name, tier="unavailable", build_error=neg_reason)

        model = self._sig.get_model(mid)
        if model is not None:
            return TreatmentKMEvidence(
                drug=drug_name,
                tier="cohort_reference",
                reference_km=model.reference_km,
                n_total=model.n_training_samples,
                caveat=COHORT_REFERENCE_CAVEAT,
            )

        if mid not in self._building:
            asyncio.create_task(
                self._build_and_cache_negative(cancer_key, entry, mid),
                name=f"treatment_build_{mid}",
            )
        return TreatmentKMEvidence(drug=drug_name, tier="unavailable", is_building=True)

    def _match_curated_entry(self, cancer_key: str, drug_name: str) -> Optional[dict[str, str]]:
        """Fuzzy-match a suggested drug name against the curated
        TREATMENT_QUERIES entries for this cancer type (entries are named by
        drug class, e.g. "Hormone therapy (tamoxifen / AI)")."""
        tokens = _drug_name_tokens(drug_name)
        if not tokens:
            return None
        for entry in TREATMENT_QUERIES.get(cancer_key, []):
            name_norm = _normalize_drug_name(entry["name"])
            if any(t in name_norm for t in tokens):
                return entry
        return None

    async def _build_and_cache_negative(
        self, cancer_type: str, entry: dict[str, str], mid: str
    ) -> None:
        """Wraps `_build_treatment_model`; records a negative-cache entry when
        the build produced no usable model, so repeat requests for this drug
        don't re-trigger a fresh orchestrator run within the TTL window."""
        await self._build_treatment_model(cancer_type, entry)
        if self._sig.get_model(mid) is None:
            self._negative_cache_put(mid, "No matching GEO cohort data available for this drug.")

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
                self._build_treatment_model(cancer_type.lower(), entry),
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
                self._build_treatment_model(cancer_type, entry),
                name=f"treatment_build_{mid}",
            )

        return TreatmentComparison(
            name=entry["name"], slug=entry["slug"], is_building=True,
        )

    async def _build_treatment_model(
        self, cancer_type: str, entry: dict[str, str]
    ) -> None:
        """Background: build a treatment-specific signature model and persist it.

        Always invoked via `asyncio.create_task` — this coroutine outlives the
        HTTP request that queued it, so it opens its own DB session rather
        than reusing a request-scoped one, which SQLAlchemy's async engine
        forbids using concurrently across tasks ("This session is
        provisioning a new connection; concurrent operations are not
        permitted").
        """
        from app.services.analysis_result_service import analysis_result_service

        mid = _model_id(cancer_type, entry["slug"])
        if mid in self._building:
            return
        self._building.add(mid)
        logger.info("Treatment model build started: %s (%s)", mid, entry["query"])

        try:
            # Try to find a cached GEO analysis matching this query first.
            async with get_db_session() as db:
                cached = await analysis_result_service.find_recent_by_query(db, entry["query"])
                full = (
                    await analysis_result_service.get_result(db, cached["result_id"])
                    if cached and cached.get("result_id") else None
                )
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
