"""Tests for the treatment-curve (F24b) cost fixes.

Building a curve for an uncurated drug used to run a full genome-wide
orchestrator pass per drug, unbounded, and could outrun the UI's poll timeout.
These cover the three things that now bound it:

  * GEO queries are built so the orchestrator recognises the cancer type
    (and no longer mis-detects one via a substring match on a short acronym);
  * `analyze_query` can be told to stop retrying instead of walking its whole
    ranked list;
  * the arm-comparison curve — the thing actually rendered — is resolved from
    clinical metadata alone, with no probe->gene mapping and no Cox pass.

All offline: the orchestrator and loader are stubbed.
"""

import asyncio
from types import SimpleNamespace

import pandas as pd
import pytest

from app.services.geo_survival_workflow_orchestrator import GEOSurvivalWorkflowOrchestrator
from app.services.signature_service import SignatureService
from app.services.treatment_context_service import (
    TreatmentContextService,
    _FASTPATH_CANDIDATES,
    _drug_query,
)


# ---------- query construction ----------

def _disease_keywords(query: str):
    return GEOSurvivalWorkflowOrchestrator._extract_keywords(
        SimpleNamespace(), query
    )[0]


def test_synthesized_drug_query_is_recognised_as_its_cancer_type():
    """The bare TREATMENT_QUERIES key ("lung") matches none of the phrases
    `_extract_keywords` looks for, so the query has to carry the canonical
    phrase or the search is built from OR'd loose words."""
    assert _drug_query("lung", "NIVOLUMAB") == "lung cancer NIVOLUMAB overall survival"
    assert _disease_keywords(_drug_query("lung", "NIVOLUMAB")) == [
        "lung cancer", "lung carcinoma",
    ]
    assert _disease_keywords(_drug_query("breast", "PALBOCICLIB")) == [
        "breast cancer", "breast carcinoma",
    ]


def test_unknown_cancer_key_still_produces_a_usable_query():
    assert _drug_query("sarcoma", "DRUG-X") == "sarcoma DRUG-X overall survival"


def test_short_acronyms_are_matched_on_word_boundaries():
    """'ALL' (acute lymphoblastic leukemia) is a cancer term AND a substring of
    'overall'. Matched as a substring, every query ending in "overall survival"
    without an earlier match was classified as leukemia and sent to GEO looking
    for leukemia series — whatever the patient's actual cancer."""
    assert _disease_keywords("sarcoma overall survival") != ["leukemia", "AML"]
    assert _disease_keywords("lung NIVOLUMAB overall survival") != ["leukemia", "AML"]
    # A genuine mention still resolves.
    assert _disease_keywords("ALL pediatric relapse survival") == ["leukemia", "AML"]


# ---------- retry-loop bounding ----------

def _orchestrator_with_ranked(n_datasets: int):
    """A real orchestrator with its network/LLM/analysis steps stubbed, so the
    only thing under test is how many datasets the retry loop reaches for."""
    from collections import OrderedDict
    orch = GEOSurvivalWorkflowOrchestrator.__new__(GEOSurvivalWorkflowOrchestrator)
    orch._analysis_cache = OrderedDict()
    orch._ANALYSIS_CACHE_MAX = 10
    orch.current_model = "mistral"
    orch.survival_service = SimpleNamespace(
        hazard_ratio_upper=1.2, hazard_ratio_lower=0.8,
    )
    datasets = [SimpleNamespace(accession=f"GSE{i}") for i in range(n_datasets)]
    seen: list[str] = []

    async def _search_geo(*_a, **_k):
        return SimpleNamespace(datasets=datasets)

    async def _rank_datasets(ds, *_a, **_k):
        return list(ds), 0.9, None

    async def _preload_platforms(*_a, **_k):
        return None

    async def _analyze_datasets_survival(batch, **_k):
        seen.extend(d.accession for d in batch)
        return []  # nothing ever succeeds -> the loop keeps reaching for more

    orch._search_geo = _search_geo
    orch._rank_datasets = _rank_datasets
    orch._preload_platforms = _preload_platforms
    orch._analyze_datasets_survival = _analyze_datasets_survival
    return orch, seen


def test_retry_loop_walks_everything_by_default():
    """Default (interactive search) behaviour is unchanged: a user waiting on
    the one analysis they asked for gets the full ranked list tried."""
    orch, seen = _orchestrator_with_ranked(30)
    asyncio.run(orch.analyze_query(query="lung cancer overall survival", max_datasets=10))
    assert len(seen) == 30


def test_max_retry_batches_stops_the_walk():
    orch, seen = _orchestrator_with_ranked(30)
    asyncio.run(orch.analyze_query(
        query="lung cancer NIVOLUMAB overall survival",
        max_datasets=10, max_retry_batches=1,
    ))
    # Initial batch of 10 plus exactly one retry batch.
    assert len(seen) == 20, f"expected 20 datasets tried, got {len(seen)}"


# ---------- metadata-only fast path ----------

def _cohort_metadata(n=60):
    """A cohort whose clinical annotations carry survival + a treatment arm."""
    return pd.DataFrame(
        {
            "os_time": [30 + (i * 7) % 900 for i in range(n)],
            "os_event": [i % 3 == 0 for i in range(n)],
            "chemotherapy": ["Yes" if i % 2 == 0 else "No" for i in range(n)],
        },
        index=[f"GSM{i}" for i in range(n)],
    )


def _fastpath_service(monkeypatch, *, gene_mapping_tripwire):
    """TreatmentContextService wired to a stub orchestrator whose loader serves
    metadata only. `gene_mapping_tripwire` fires if the expensive probe->gene
    path is touched."""
    sig = SignatureService(orchestrator=None)

    async def _load_metadata_only(ds):
        return SimpleNamespace(
            accession=ds.accession, title=ds.accession,
            sample_metadata=_cohort_metadata(),
            expression_matrix=pd.DataFrame(),
        )

    async def _apply_gene_mapping(*_a, **_k):
        gene_mapping_tripwire.append("called")
        raise AssertionError("fast path must not map probes to genes")

    async def _search_geo(*_a, **_k):
        return SimpleNamespace(
            datasets=[SimpleNamespace(accession=f"GSE{i}") for i in range(8)]
        )

    async def _rank_datasets(ds, *_a, **_k):
        return list(ds), 0.9, None

    async def _analyze_query(*_a, **_k):
        raise AssertionError("fast path must not run the gene pipeline")

    sig.orchestrator = SimpleNamespace(
        loader_service=SimpleNamespace(
            load_metadata_only=_load_metadata_only,
            apply_gene_mapping=_apply_gene_mapping,
        ),
        survival_service=SimpleNamespace(),
        _search_geo=_search_geo,
        _rank_datasets=_rank_datasets,
        analyze_query=_analyze_query,
    )
    return TreatmentContextService(sig)


def test_fast_path_returns_arm_comparison_without_touching_expression(monkeypatch):
    tripwire: list[str] = []
    svc = _fastpath_service(monkeypatch, gene_mapping_tripwire=tripwire)

    real_sig = SignatureService(orchestrator=None)

    async def _extract(loaded, prefer_regex=False):
        """Stand in for the LLM-backed column detection."""
        meta = loaded.sample_metadata
        surv = pd.DataFrame({
            "time": meta["os_time"].astype(float),
            "event": meta["os_event"].astype(int),
        }, index=meta.index)
        binary = (meta["chemotherapy"] == "Yes").astype(int)
        return surv, binary, {0: "No", 1: "Yes"}, "chemotherapy"

    svc._sig.extract_treatment_arms = _extract
    svc._sig.match_treatment_arm_km = real_sig.match_treatment_arm_km
    # The real fitter, so the arms are validated against the real schema.
    from app.services.survival_analysis_service import SurvivalAnalysisService
    svc._sig.orchestrator.survival_service._fit_treatment_arm_km = (
        SurvivalAnalysisService(min_samples_per_group=5)._fit_treatment_arm_km
    )

    evidence, n_candidates = asyncio.run(svc.find_arm_cohort_for_drug(
        "lung", {"query": "lung cancer NIVOLUMAB overall survival",
                 "slug": "nivolumab", "name": "NIVOLUMAB"},
        "NIVOLUMAB",
    ))

    assert evidence is not None
    assert evidence.tier == "arm_comparison"
    assert evidence.arms and len(evidence.arms) == 2
    assert evidence.arm_variable == "chemotherapy"
    assert evidence.accession == "GSE0", "should stop at the first usable cohort"
    assert not tripwire, "fast path must not touch probe->gene mapping"


def test_fast_path_reports_zero_candidates_when_geo_finds_nothing():
    """The pre-screen: a drug with no GEO footprint must be distinguishable
    from one whose cohorts simply had no usable arm split, so the caller can
    negative-cache it instead of starting a build."""
    sig = SignatureService(orchestrator=None)

    async def _search_geo(*_a, **_k):
        return SimpleNamespace(datasets=[])

    sig.orchestrator = SimpleNamespace(_search_geo=_search_geo)
    svc = TreatmentContextService(sig)

    evidence, n_candidates = asyncio.run(svc.find_arm_cohort_for_drug(
        "lung", {"query": "lung cancer APOMAB overall survival",
                 "slug": "apomab", "name": "APOMAB"},
        "APOMAB",
    ))
    assert evidence is None
    assert n_candidates == 0


def test_pre_screen_negative_caches_instead_of_building():
    sig = SignatureService(orchestrator=None)
    svc = TreatmentContextService(sig)

    async def _no_candidates(*_a, **_k):
        return None, 0

    async def _must_not_build(*_a, **_k):
        raise AssertionError("a drug with no GEO cohorts must not trigger a build")

    svc.find_arm_cohort_for_drug = _no_candidates
    svc._build_treatment_model = _must_not_build

    mid = "treatment_lung_apomab"
    asyncio.run(svc._resolve_drug_evidence(
        "lung", {"query": "q", "slug": "apomab", "name": "APOMAB"}, mid, "APOMAB",
    ))
    assert svc._negative_cache_get(mid) is not None


def test_fast_path_result_is_cached_and_short_circuits_later_lookups():
    sig = SignatureService(orchestrator=None)
    svc = TreatmentContextService(sig)

    from app.models.signature_models import TreatmentKMEvidence
    found = TreatmentKMEvidence(
        drug="NIVOLUMAB", tier="arm_comparison", accession="GSE123",
    )

    calls: list[str] = []

    async def _finds_it(*_a, **_k):
        calls.append("searched")
        return found, 3

    async def _must_not_build(*_a, **_k):
        raise AssertionError("fast-path hit must not fall through to a build")

    svc.find_arm_cohort_for_drug = _finds_it
    svc._build_treatment_model = _must_not_build

    mid = "treatment_lung_nivolumab"
    asyncio.run(svc._resolve_drug_evidence(
        "lung", {"query": "q", "slug": "nivolumab", "name": "NIVOLUMAB"},
        mid, "NIVOLUMAB",
    ))

    cached = svc._arm_cohort_cache.get(mid)
    assert cached is not None and cached.accession == "GSE123"
    assert len(calls) == 1


def test_concurrent_polls_do_not_duplicate_a_resolution():
    """The UI re-polls every 15 s and one resolution takes longer than that.

    `asyncio.create_task` only SCHEDULES — so claiming the mid inside the task
    body left a window in which every caller arriving before the body first ran
    saw an unclaimed mid and spawned its own duplicate. Production hit exactly
    this: eight drugs resolving at once produced two concurrent builds of the
    same model. The claim has to happen synchronously in the caller.
    """
    from app.models.signature_models import PrognosticModel

    sig = SignatureService(orchestrator=None)
    svc = TreatmentContextService(sig)
    sig.get_model = lambda mid: None

    starts: list[str] = []

    async def _slow_resolve(*_a, **_k):
        starts.append("resolved")
        await asyncio.sleep(0.05)
        return None, 3

    async def _noop_build(*_a, **_k):
        return None

    svc.find_arm_cohort_for_drug = _slow_resolve
    svc._guarded_build = _noop_build

    async def _race():
        # Four callers in the SAME tick, before any spawned task body can run.
        await asyncio.gather(*[
            svc.get_or_build_km_for_drug("breast", "PACLITAXEL") for _ in range(4)
        ])
        # Let the spawned resolution finish.
        await asyncio.sleep(0.3)

    asyncio.run(_race())
    assert len(starts) == 1, f"expected one resolution, got {len(starts)}"
    assert not svc._building, "claim must be released when done"


def test_scheduled_resolution_respects_a_negative_cache_written_meanwhile():
    """A task scheduled before an earlier resolution finished must not redo the
    work. In production the pre-screen negative-cached five drugs, then a second
    already-scheduled task for each ran anyway and started a full 8-minute build
    of the drug that had just been ruled out."""
    sig = SignatureService(orchestrator=None)
    svc = TreatmentContextService(sig)

    async def _must_not_run(*_a, **_k):
        raise AssertionError("already-answered mid must not be resolved again")

    svc.find_arm_cohort_for_drug = _must_not_run
    svc._guarded_build = _must_not_run

    mid = "treatment_breast_cytarabine"
    svc._negative_cache_put(mid, "No GEO cohort in this cancer type records this agent.")

    asyncio.run(svc._resolve_drug_evidence(
        "breast", {"query": "q", "slug": "cytarabine", "name": "CYTARABINE"},
        mid, "CYTARABINE",
    ))


def test_client_setting_overrides_the_models_cancer_genes_flag():
    """A demo/curated model always carries cancer_genes_only=False, so inheriting
    from the model alone made every Tier-2 build run genome-wide regardless of
    what the user had ticked."""
    from app.api.chat_routes import CohortKMRequest, TherapyRationaleRequest

    assert CohortKMRequest(model_id="m").cancer_genes_only is None
    assert CohortKMRequest(model_id="m", cancer_genes_only=True).cancer_genes_only is True
    assert TherapyRationaleRequest(model_id="m", cancer_genes_only=True).cancer_genes_only is True

    model = SimpleNamespace(cancer_genes_only=False)
    for client_value, expected in [(None, False), (True, True), (False, False)]:
        resolved = (
            model.cancer_genes_only if client_value is None else client_value
        )
        assert resolved is expected


# ---------- platform-size cap ----------

def test_oversized_uncached_platforms_are_dropped():
    """A multi-GB GPL annotation is minutes of download for one cohort, and no
    gene filter avoids it — cancer_genes_only is applied AFTER probe->gene
    mapping. Background builds skip those cohorts; a platform already mapped on
    disk is free to reuse no matter how big the original file was."""
    orch = GEOSurvivalWorkflowOrchestrator.__new__(GEOSurvivalWorkflowOrchestrator)

    sizes = {"GPL_SMALL": 40.0, "GPL_HUGE": 12518.0, "GPL_CACHED": 4617.0}

    async def _size(platform):
        return sizes.get(platform)

    class _GMS:
        # Only GPL_CACHED already has a built mapping on disk.
        def _get_prebuilt_mapping_path(self, platform):
            return "/some/path.parquet" if platform == "GPL_CACHED" else None
        get_platform_size_mb = staticmethod(_size)

    orch.loader_service = SimpleNamespace(gene_mapping_service=_GMS())

    datasets = [
        SimpleNamespace(accession="GSE_small", platforms=["GPL_SMALL"]),
        SimpleNamespace(accession="GSE_huge", platforms=["GPL_HUGE"]),
        SimpleNamespace(accession="GSE_cached_huge", platforms=["GPL_CACHED"]),
        SimpleNamespace(accession="GSE_none", platforms=[]),
    ]
    kept = asyncio.run(orch._drop_oversized_platforms(datasets, 500.0))
    accessions = [d.accession for d in kept]

    assert "GSE_huge" not in accessions, "uncached 12 GB platform must be skipped"
    assert accessions == ["GSE_small", "GSE_cached_huge", "GSE_none"]


def test_platform_cap_is_off_by_default_for_interactive_search():
    """The interactive search must keep paying for big platforms — the user
    asked about those specific cohorts."""
    import inspect
    sig = inspect.signature(GEOSurvivalWorkflowOrchestrator.analyze_query)
    assert sig.parameters["max_platform_mb"].default is None
