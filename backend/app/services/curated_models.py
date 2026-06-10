"""Curated prognostic models for Oncologist Mode.

Each curated cancer type gets one durable, version-pinned `PrognosticModel`
(combined clinical + expression) so an oncologist can pick a cancer and score a
patient instantly — no on-the-fly signature building.

Build policy (idempotent):
  1. If a model for the cancer is already loaded/persisted, keep it.
  2. Otherwise prefer a REAL build from the curated cancer's pre-run analysis
     result (cross-cohort, validated).
  3. If no cached analysis / cohorts are available (common in fresh dev), fall
     back to a synthetic DEMO model tagged with the cancer type, so the patient
     flow is fully exercisable offline. `is_demo=True` is surfaced to the UI.

Model ids are stable (`curated_<key>`) so a later real build cleanly replaces
an earlier demo one.
"""

from __future__ import annotations

import logging
from typing import Dict

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.analysis_result_service import analysis_result_service
from app.services.signature_service import SignatureService

logger = logging.getLogger(__name__)


async def ensure_curated_models(
    signature_service: SignatureService,
    db: AsyncSession,
    prefer_real: bool = True,
    force: bool = False,
) -> Dict[str, str]:
    """Ensure every curated cancer type has a durable prognostic model.

    Behaviour:
      * A real model already present → kept (unless `force`).
      * A DEMO model present + `prefer_real` → re-attempt a real build, so the
        moment cohorts are cached a restart upgrades demo → real; the demo is
        retained if the real build still can't run.
      * Nothing present → real build, falling back to a synthetic demo model.

    Returns a {cancer_key: model_id} map. Resilient: a failure for one cancer
    never blocks the others or startup.
    """
    # Imported here to avoid a circular import at module load.
    from app.api.gallery_routes import CURATED_CANCERS

    built: Dict[str, str] = {}
    for entry in CURATED_CANCERS:
        key = entry["key"]
        existing = signature_service.find_model_by_cancer(key)
        # Keep a usable model unless it's a demo we'd like to upgrade, or forced.
        if existing is not None and not force and not (prefer_real and existing.is_demo):
            built[key] = existing.model_id
            continue

        model = None
        if prefer_real or force:
            try:
                cached = await analysis_result_service.find_recent_by_query(db, entry["query"])
                if cached and cached.get("result_id"):
                    full = await analysis_result_service.get_result(db, cached["result_id"])
                    if full:
                        model = await signature_service.build_from_result(full, cancer_type=key)
                        logger.info("Built REAL curated model for %s", key)
            except (ValueError, KeyError, OSError, RuntimeError) as e:
                logger.warning("Real curated build failed for %s (%s)", key, e)

        if model is None:
            if existing is not None and not force:
                # Couldn't upgrade — keep the existing demo, don't churn a new one.
                built[key] = existing.model_id
                continue
            # No model yet, or a forced refresh: (re)build the synthetic demo.
            model = signature_service.build_demo_signature(query=entry["query"], cancer_type=key)
            logger.info("Built DEMO curated model for %s", key)

        # Stable id so a later real build replaces this artifact in place.
        model.model_id = f"curated_{key}"
        signature_service.save_model_to_disk(model)
        built[key] = model.model_id

    return built
