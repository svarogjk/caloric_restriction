"""Tests for Oncologist Mode: combined clinical+expression model, durable
persistence, and the grounded therapy-rationale guardrails.

All synchronous and offline (demo signature + bundled therapy index); the one
async path (the no-evidence endpoint branch, which returns before any LLM call)
is driven with `asyncio.run`.
"""

import asyncio

import pytest

from app.services.signature_service import SignatureService


# ---------- combined clinical + expression model ----------

def _demo_model():
    return SignatureService(orchestrator=None).build_demo_signature(max_genes=10)


def test_combined_model_has_clinical_covariates():
    model = _demo_model()
    names = {c.name for c in model.clinical_covariates}
    assert {"age", "grade"} <= names, f"expected age+grade covariates, got {names}"

    kinds = {c.name: c.kind for c in model.clinical_covariates}
    assert kinds["age"] == "numeric"
    assert kinds["grade"] == "categorical"

    grade = next(c for c in model.clinical_covariates if c.name == "grade")
    assert grade.options and grade.reference_category in grade.options

    # Combined model is populated and the incremental-value metrics exist.
    assert model.combined_reference_km is not None
    assert len(model.combined_risk_tertiles) == 2
    assert model.c_index_combined is not None
    assert model.c_index_expression_only is not None
    assert model.delta_c_index is not None


def test_combined_vs_expression_only_scoring():
    svc = SignatureService(orchestrator=None)
    model = svc.build_demo_signature(max_genes=10)
    patient = svc.build_demo_patient(model)

    combined = svc.score_single_sample(model, patient, clinical={"age": 70, "grade": "3"})
    assert combined.scored_on == "combined"
    assert any(c.kind == "clinical" for c in combined.contributions)
    assert any(c.kind == "expression" for c in combined.contributions)

    fallback = svc.score_single_sample(model, patient)
    assert fallback.scored_on == "expression-only (clinical omitted)"
    assert all(c.kind == "expression" for c in fallback.contributions)


def test_clinical_covariates_move_the_score():
    """Holding expression fixed, a higher-grade / older patient should not score
    identically to a low-grade / younger one."""
    svc = SignatureService(orchestrator=None)
    model = svc.build_demo_signature(max_genes=10)
    patient = svc.build_demo_patient(model)
    grade = next(c for c in model.clinical_covariates if c.name == "grade")
    ref_grade = grade.reference_category
    high_grade = next((lvl for lvl in grade.options if lvl != ref_grade), ref_grade)

    high = svc.score_single_sample(model, patient, clinical={"age": 85, "grade": high_grade})
    low = svc.score_single_sample(model, patient, clinical={"age": 40, "grade": ref_grade})
    assert high.risk_score != low.risk_score


# ---------- durable persistence + pinning ----------

def test_persistence_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr(SignatureService, "_MODELS_DIR", tmp_path)
    svc = SignatureService(orchestrator=None)
    model = svc.build_demo_signature(max_genes=8)
    model.model_id = "curated_test"
    svc.save_model_to_disk(model)
    assert (tmp_path / "curated_test.json").exists()

    # Fresh service loads it from disk and can score against it.
    svc2 = SignatureService(orchestrator=None)
    assert svc2.load_persisted_models() >= 1
    reloaded = svc2.get_model("curated_test")
    assert reloaded is not None
    assert reloaded.model_id == "curated_test"
    # Clinical covariates survive the JSON round-trip.
    assert {c.name for c in reloaded.clinical_covariates} == {c.name for c in model.clinical_covariates}
    assert svc2.find_model_by_cancer("demo") is not None


def test_pinned_models_survive_eviction(tmp_path, monkeypatch):
    monkeypatch.setattr(SignatureService, "_MODELS_DIR", tmp_path)
    svc = SignatureService(orchestrator=None)
    svc._MODELS_MAX = 2
    pinned = svc.build_demo_signature(max_genes=6)
    pinned.model_id = "curated_pinned"
    svc.save_model_to_disk(pinned)  # pinned

    # Churn several non-pinned models past the cap; pinned one must remain.
    for i in range(5):
        m = svc.build_demo_signature(max_genes=6)
        m.model_id = f"ephemeral_{i}"
        svc._put_model(m)
    assert svc.get_model("curated_pinned") is not None


# ---------- therapy-rationale guardrails ----------

def test_prescribing_guardrail_regex():
    from app.api.chat_routes import _PRESCRIBING_PATTERN

    directives = [
        "Administer trastuzumab to this patient.",
        "The patient should receive erlotinib.",
        "We recommend starting dabrafenib.",
        "Prescribe lapatinib based on ERBB2.",
    ]
    hypotheses = [
        "CIViC documents ERBB2 sensitivity to neratinib; worth discussing as a hypothesis.",
        "EGFR-targeted agents are associated with response in CIViC; prognostic context only.",
    ]
    assert all(_PRESCRIBING_PATTERN.search(s) for s in directives)
    assert not any(_PRESCRIBING_PATTERN.search(s) for s in hypotheses)


def test_therapy_rationale_no_evidence_path():
    """When no documented evidence exists, the endpoint returns an honest
    'none found' message and never calls the LLM (so this runs offline)."""
    from app.api import chat_routes
    from app.api.chat_routes import TherapyRationaleRequest, therapy_rationale

    svc = SignatureService(orchestrator=None)
    model = svc.build_demo_signature(max_genes=6)  # genes DEMOG* -> no KB evidence

    class _EmptyTherapy:
        def lookup(self, genes, max_total=40):
            return []

    chat_routes.set_therapy_services(svc, _EmptyTherapy())
    resp = asyncio.run(therapy_rationale(TherapyRationaleRequest(model_id=model.model_id)))
    assert resp.evidence == []
    assert "no documented" in resp.rationale.lower()
    assert resp.domain_score == 0


# ---------- per-treatment KM evidence (F24b) ----------

def test_match_treatment_arm_km_matches_via_synonym():
    """A GEO arm labeled with a research code ("PXD101") that doesn't
    literally contain the DGIdb/CIViC drug name ("Belinostat") must still be
    attributed when that code is a known synonym — otherwise real,
    already-downloaded cohort data is silently missed on a naming
    technicality."""
    import pandas as pd

    class _FakeSurvivalService:
        def _fit_treatment_arm_km(self, time_col, event_col, treatment_binary, arm_names):
            return [
                {
                    "name": arm_names[0], "n_samples": 12, "n_events": 4,
                    "km_curve": {"times": [0, 1], "survival_probabilities": [1.0, 0.8],
                                 "ci_lower": None, "ci_upper": None, "n_samples": 12, "n_events": 4},
                },
                {
                    "name": arm_names[1], "n_samples": 12, "n_events": 3,
                    "km_curve": {"times": [0, 1], "survival_probabilities": [1.0, 0.9],
                                 "ci_lower": None, "ci_upper": None, "n_samples": 12, "n_events": 3},
                },
            ]

    class _FakeOrchestrator:
        survival_service = _FakeSurvivalService()

    svc = SignatureService(orchestrator=_FakeOrchestrator())
    survival_df = pd.DataFrame({"time": [1, 2], "event": [1, 0]})
    treatment_binary = pd.Series([0, 1])
    arm_names = {0: "Untreated/control", 1: "PXD101"}

    # No synonym -> the literal drug name doesn't appear in "PXD101" -> no match.
    assert svc.match_treatment_arm_km(survival_df, treatment_binary, arm_names, "Belinostat") is None

    # With the research-code synonym -> real data is recovered.
    arms = svc.match_treatment_arm_km(
        survival_df, treatment_binary, arm_names, "Belinostat", synonyms=["PXD101", "Beleodaq"]
    )
    assert arms is not None
    assert {a.name for a in arms} == {"Untreated/control", "PXD101"}


def test_select_top_drugs_dedupes_and_breaks_ties_by_evidence_strength():
    from app.api.chat_routes import _select_top_drugs

    evidence = [
        {"gene": "ERCC1", "drug": "Cisplatin", "source": "CIViC", "evidence_level": "B"},
        {"gene": "TP53", "drug": "cisplatin", "source": "CIViC", "evidence_level": "A"},  # dup, higher level
    ]
    picked = _select_top_drugs(evidence, max_n=5)
    assert len(picked) == len({p.lower() for p in picked})  # deduped
    assert picked[0].lower() == "cisplatin"


def test_select_top_drugs_no_longer_excludes_investigational_or_low_evidence():
    """Approval status / CIViC level is a within-gene tiebreaker only now —
    it must not gate eligibility, since it has no bearing on whether a
    matching GEO cohort actually exists (the bug this fixes)."""
    from app.api.chat_routes import _select_top_drugs

    evidence = [
        {"gene": "NOTCH2", "drug": "Nirogacestat", "source": "DGIdb", "approved": False},
        {"gene": "APC", "drug": "JW55", "source": "CIViC", "evidence_level": "D"},
    ]
    picked = _select_top_drugs(evidence, max_n=5)
    assert any(d.lower() == "nirogacestat" for d in picked)
    assert any(d.lower() == "jw55" for d in picked)


def test_select_top_drugs_round_robins_across_genes():
    """One gene's several approved drugs must not consume the whole budget
    and starve other genes of any lookup at all."""
    from app.api.chat_routes import _select_top_drugs

    evidence = [
        {"gene": "HDAC4", "drug": f"HDACi{i}", "source": "DGIdb", "approved": True}
        for i in range(4)
    ] + [
        {"gene": "NOTCH2", "drug": "Nirogacestat", "source": "DGIdb", "approved": False},
        {"gene": "APC", "drug": "JW55", "source": "CIViC", "evidence_level": "D"},
    ]
    picked = _select_top_drugs(evidence, max_n=3)
    picked_genes = set()
    by_drug = {e["drug"].lower(): e["gene"] for e in evidence}
    for d in picked:
        picked_genes.add(by_drug[d.lower()])
    assert picked_genes == {"HDAC4", "NOTCH2", "APC"}  # every gene got at least one shot


def test_select_top_drugs_respects_max_n():
    from app.api.chat_routes import _select_top_drugs

    evidence = [
        {"gene": f"G{i}", "drug": f"Drug{i}", "source": "CIViC", "evidence_level": "A"}
        for i in range(8)
    ]
    assert len(_select_top_drugs(evidence, max_n=5)) == 5


def test_resolve_cohort_km_falls_back_to_unavailable_offline(monkeypatch):
    """With no orchestrator (so Tier 1 is unreachable) and no treatment-context
    service initialised (so Tier 2's build can't be queued), cohort KM
    resolution degrades to an honest Tier-3 'unavailable' result — never a
    fabricated curve. The PubChem synonym lookup is stubbed so this test
    stays offline."""
    from app.api import chat_routes
    from app.api.chat_routes import _resolve_cohort_km

    class _NoSynonyms:
        async def get_synonyms(self, drug_name):
            return []

    monkeypatch.setattr(chat_routes, "get_drug_synonym_service", lambda: _NoSynonyms())

    svc = SignatureService(orchestrator=None)
    model = svc.build_demo_signature(max_genes=6)
    chat_routes.set_therapy_services(svc, object())

    result = asyncio.run(_resolve_cohort_km(model, "Cisplatin", {}))
    assert result.tier == "unavailable"
    assert result.arms is None
    assert result.reference_km is None
    assert result.build_error


def test_therapy_rationale_marks_unbudgeted_drugs_not_checked(monkeypatch):
    """Every evidence row must get an explicit cohort_km tier — including
    'not_checked' for drugs outside this round's lookup budget — instead of
    a silent None the UI has no way to explain."""
    from app.api import chat_routes
    from app.api.chat_routes import TherapyRationaleRequest, therapy_rationale
    from app.models.signature_models import TreatmentKMEvidence

    svc = SignatureService(orchestrator=None)
    model = svc.build_demo_signature(max_genes=6)

    evidence = [
        {"gene": "GENE1", "drug": "DrugA", "source": "DGIdb", "approved": True},
        {"gene": "GENE2", "drug": "DrugB", "source": "DGIdb", "approved": True},
    ]

    class _FixedTherapy:
        def lookup(self, genes, max_total=40):
            return evidence

    async def fake_generate_response(self, messages, model, conversation_id):
        return "Advisory hypothesis-only text.", 0, 40

    class _FakePydanticAI:
        async def generate_response(self, messages, model, conversation_id):
            return "Advisory hypothesis-only text.", 0, 40

    async def fake_resolve(model_arg, drug, cache, expression=None, clinical=None):
        return TreatmentKMEvidence(drug=drug, tier="unavailable", build_error="no data")

    chat_routes.set_therapy_services(svc, _FixedTherapy())
    monkeypatch.setattr(chat_routes, "get_pydantic_ai_service", lambda: _FakePydanticAI())
    monkeypatch.setattr(chat_routes, "_select_top_drugs", lambda evidence: ["DrugA"])
    monkeypatch.setattr(chat_routes, "_resolve_cohort_km", fake_resolve)

    resp = asyncio.run(therapy_rationale(TherapyRationaleRequest(model_id=model.model_id)))
    by_drug = {r.drug: r for r in resp.evidence}
    assert by_drug["DrugA"].cohort_km.tier == "unavailable"
    assert by_drug["DrugB"].cohort_km.tier == "not_checked"


# ---------- cross-platform normalization + input-validity warnings ----------

def _full_profile(model, rng_seed=7):
    """A full-ish profile (>= _QN_MIN_GENES) containing the signature genes plus filler."""
    import numpy as np
    rng = np.random.default_rng(rng_seed)
    profile = {g.gene_symbol: float(g.ref_quantiles[60]) for g in model.genes}
    for i in range(50):
        profile[f'FILLER{i}'] = float(rng.normal(0, 1))
    return profile


def test_quantile_normalize_monotonic():
    from app.services.signature_service import quantile_normalize_to_reference
    ref = [float(i) for i in range(100)]  # 0..99
    mapped = quantile_normalize_to_reference({'A': 1.0, 'B': 5.0, 'C': 3.0}, ref)
    # Ordering is preserved and values land within the reference range.
    assert mapped['A'] < mapped['C'] < mapped['B']
    assert all(0 <= v <= 99 for v in mapped.values())


def test_full_profile_uses_quantile_normalization():
    svc = SignatureService(orchestrator=None)
    model = svc.build_demo_signature(max_genes=10)
    r = svc.score_single_sample(model, _full_profile(model))
    assert 'quantile-normalized' in r.normalization
    assert not any('per-gene rank' in w for w in r.warnings)


def test_sparse_profile_falls_back_and_warns():
    svc = SignatureService(orchestrator=None)
    model = svc.build_demo_signature(max_genes=10)
    r = svc.score_single_sample(model, svc.build_demo_patient(model))  # only signature genes
    assert 'per-gene rank' in r.normalization
    assert any('genes provided' in w for w in r.warnings)


def test_scale_mismatch_warning():
    svc = SignatureService(orchestrator=None)
    model = svc.build_demo_signature(max_genes=10)
    # Sparse input with values far outside the reference (~standard-normal) range.
    wild = {g.gene_symbol: 5000.0 for g in model.genes}
    r = svc.score_single_sample(model, wild)
    assert any('outside the reference' in w for w in r.warnings)


def test_clinical_category_and_range_warnings():
    svc = SignatureService(orchestrator=None)
    model = svc.build_demo_signature(max_genes=10)
    r = svc.score_single_sample(
        model, _full_profile(model), clinical={'age': 250, 'grade': 'G7'}
    )
    assert any('outside the training range' in w for w in r.warnings)
    assert any("'G7'" in w and 'not seen in training' in w for w in r.warnings)


# ---------- unified personalization (auto-build + score) ----------

def test_get_or_build_for_result_caches():
    """Personalizing the same analysis twice reuses one auto-built signature."""
    svc = SignatureService(orchestrator=None)
    calls = {"n": 0}

    async def fake_build(result, max_genes=15, cancer_type=None):
        calls["n"] += 1
        return svc.build_demo_signature(max_genes=6)

    svc.build_from_result = fake_build
    a = asyncio.run(svc.get_or_build_for_result("R1", {}))
    b = asyncio.run(svc.get_or_build_for_result("R1", {}))
    assert a.model_id == b.model_id
    assert calls["n"] == 1  # built once, reused second time


def test_personalize_endpoint_model_id_path():
    """The unified /personalize endpoint scores against a locked model id."""
    from app.api import signature_routes
    from app.api.signature_routes import PersonalizeRequest, personalize

    svc = SignatureService(orchestrator=None)
    model = svc.build_demo_signature(max_genes=8)
    signature_routes.set_signature_service(svc)

    resp = asyncio.run(
        personalize(
            PersonalizeRequest(
                model_id=model.model_id,
                expression=svc.build_demo_patient(model),
                clinical={"age": 70, "grade": "3"},
            ),
            db=None,
        )
    )
    assert resp.model_id == model.model_id
    assert resp.prediction.scored_on == "combined"
    assert {c["name"] for c in resp.clinical_covariates} == {"age", "grade"}


def test_therapy_evidence_lookup_if_bundled():
    """If the bundled index is present, a well-known oncogene returns real,
    attributed associations. Skips when the index hasn't been built."""
    from app.services.therapy_evidence_service import TherapyEvidenceService

    svc = TherapyEvidenceService()
    if svc.load() == 0:
        pytest.skip("therapy evidence index not bundled in this environment")
    recs = svc.lookup(["ERBB2"], max_total=5)
    assert recs, "expected documented associations for ERBB2"
    assert all(r["gene"] == "ERBB2" for r in recs)
    assert all(r["source"] in {"CIViC", "DGIdb"} for r in recs)
    assert all(r.get("drug") for r in recs)


# ---------- treatment cohort KM evidence (F24b) ----------

def test_cohort_reference_km_carries_patient_scored_group_and_units():
    """A Tier-2 cohort-reference result must describe ITS OWN cohort, not
    borrow the patient's baseline framing:

      * `matched_risk_group` comes from scoring the patient against THIS
        treatment model (its own coefficients/tertiles) — reusing the
        baseline model's risk-group label to index another model's tertile
        curves is a category error, since cutoffs differ per model.
      * `time_unit` + `accession` travel with the curve. Without the unit a
        cohort reported in years gets plotted on the same raw axis as one
        reported in days, and the resulting follow-up-length gap reads as a
        treatment effect. Without the accession the UI can't tell that
        several drugs resolved to the SAME GEO series.
    """
    from app.services.treatment_context_service import (
        TreatmentContextService, _model_id, _slugify_drug_name,
    )

    svc = SignatureService(orchestrator=None)
    model = svc.build_demo_signature(max_genes=8, cancer_type="breast")
    model.time_unit = "years"
    # Must match the id the service derives for this drug name, or the lookup
    # falls through to a background build and returns tier="unavailable".
    mid = _model_id("breast", _slugify_drug_name("FauxDrug"), False)
    model.model_id = mid
    svc._models[mid] = model

    ctx = TreatmentContextService(svc)
    patient = svc.build_demo_patient(model)

    evidence = asyncio.run(
        ctx.get_or_build_km_for_drug("breast", "FauxDrug", synonyms=["faux drug"])
    )
    # Without expression there is nothing to score against -> stays None
    # rather than silently inheriting some other model's label.
    assert evidence.tier == "cohort_reference"
    assert evidence.matched_risk_group is None
    assert evidence.time_unit == "years"
    assert evidence.accession == model.training_accession

    scored = asyncio.run(
        ctx.get_or_build_km_for_drug(
            "breast", "FauxDrug", synonyms=["faux drug"], expression=patient
        )
    )
    assert scored.matched_risk_group in {"low", "intermediate", "high"}
    assert scored.matched_risk_group == svc.score_single_sample(model, patient).risk_group


def test_build_from_result_time_unit_follows_training_cohort():
    """`_build_from_cohorts` trains on the LARGEST cohort, so the model's
    declared time_unit must come from that cohort — not from whichever
    accession happened to be iterated last. A mismatch here mislabels the
    curve's axis and corrupts every downstream comparison."""
    import pandas as pd

    svc = SignatureService(orchestrator=None)
    rng = __import__("numpy").random.default_rng(3)

    def cohort(acc, n):
        genes = [f"G{i}" for i in range(6)]
        cols = [f"{acc}_s{i}" for i in range(n)]
        expr = pd.DataFrame(rng.normal(0, 1, size=(len(genes), n)), index=genes, columns=cols)
        surv = pd.DataFrame(
            {"time": rng.uniform(1, 900, size=n), "event": rng.integers(0, 2, size=n)},
            index=cols,
        )
        return acc, expr, surv, None

    # Largest cohort is the SECOND one; its unit ("months") must win.
    built = svc._build_from_cohorts(
        query="unit test",
        cohorts=[cohort("GSE_SMALL", 40), cohort("GSE_BIG", 120)],
        time_unit="months",
        is_demo=False,
    )
    assert built.training_accession == "GSE_BIG"
    assert built.time_unit == "months"
