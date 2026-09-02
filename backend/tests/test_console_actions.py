"""Tests for the clinical console's agent-orchestrated workflow: the chart-state
system prompt block, the PatientContext privacy model, and the action-tool
intent/execution split (console_actions.py).

Action tools take a RunContext[AgentDeps]-like object; since every tool only
ever reads `ctx.deps`, a lightweight stand-in avoids constructing a real
pydantic-ai RunContext (which requires a live model + usage tracker).
"""

import asyncio
from dataclasses import dataclass, field
from typing import Any

import pytest
from pydantic import ValidationError

from app.api.chat_routes import PatientContext
from app.services.chat.agent_tools import AGENT_TOOLS, AgentDeps, get_signature_model_evidence
from app.services.chat.console_actions import (
    ACTION_TOOL_NAMES,
    ACTION_TOOLS,
    run_survival_analysis,
    set_workflow_goal,
    load_example_case,
    request_tumour_profile,
    score_patient,
    set_cancer_type,
    show_treatment_evidence,
)
from app.services.chat.pydantic_ai_service import (
    _build_chart_block,
    _build_workflow_block,
    _compute_domain_score,
)
from app.services.signature_service import SignatureService


@dataclass
class _FakeCtx:
    """Duck-typed stand-in for RunContext[AgentDeps] — tools only read ctx.deps."""
    deps: Any


def _deps(**overrides) -> AgentDeps:
    base = dict(
        rag_service=None,
        estimation_service=None,
        geo_preview_service=None,
        signature_service=SignatureService(orchestrator=None),
        action_sink=[],
    )
    base.update(overrides)
    return AgentDeps(**base)


# ---------- PatientContext privacy/validation model ----------

def test_patient_context_rejects_out_of_range_percentile():
    with pytest.raises(ValidationError):
        PatientContext(risk_percentile=120)


def test_patient_context_caps_gene_lists_at_eight():
    with pytest.raises(ValidationError):
        PatientContext(top_risk_genes=[f"G{i}" for i in range(9)])
    # Exactly 8 is fine.
    PatientContext(top_risk_genes=[f"G{i}" for i in range(8)])


def test_patient_context_has_no_value_carrying_fields():
    # Only names/symbols/counts — never raw expression or covariate values.
    fields = set(PatientContext.model_fields.keys())
    assert "expression" not in fields
    assert "clinical" not in fields
    assert "clinical_covariate_values" not in fields
    assert "clinical_covariate_names" in fields  # names only


# ---------- _build_chart_block ----------

# The chart block reports FACTS about the chart. It deliberately carries no
# "what next" line any more: it and _build_research_block used to append one
# each, so a chart with no analysis told the agent to call request_tumour_profile
# AND run_survival_analysis in the same prompt. _build_workflow_block is now the
# only place a next step is stated.

def test_chart_block_states_no_next_step():
    for ctx in ({}, {"cancer_type": "breast", "model_id": "curated_breast"}):
        assert "MISSING" not in _build_chart_block(ctx)


def test_chart_block_cancer_set_no_expression_yet():
    block = _build_chart_block({"cancer_type": "breast", "model_id": "curated_breast"})
    assert "Cancer type: breast" in block
    # Nothing about a tumour profile is reported, because none was provided...
    assert "Tumour profile" not in block
    # ...and the block states outright that the agent cannot see patient values.
    assert "cannot see the patient's identity, expression values, or clinical values" in block


def test_chart_block_scored_reports_the_score_without_values():
    ctx = {
        "cancer_type": "breast",
        "model_id": "curated_breast",
        "genes_provided": 50,
        "genes_used": 14,
        "genes_total": 15,
        "risk_group": "high",
        "risk_percentile": 82.0,
        "scored_on": "combined",
        "pooled_c_index": 0.71,
        "c_index_combined": 0.74,
        "delta_c_index": 0.03,
        "top_risk_genes": ["MKI67", "TOP2A"],
        "top_protective_genes": ["ESR1"],
        "clinical_covariate_names": ["age", "grade"],
    }
    block = _build_chart_block(ctx)
    assert "HIGH risk" in block
    assert "82th percentile" in block or "82" in block
    assert "MKI67" in block and "ESR1" in block
    assert "age" in block and "grade" in block
    # Covariate NAMES appear, but the block explicitly says values are withheld.
    assert "values NOT transmitted" in block


# ---------- Action tools: validate before recording an intent ----------

def test_set_cancer_type_rejects_unknown_key():
    deps = _deps()
    ctx = _FakeCtx(deps=deps)
    result = asyncio.run(set_cancer_type(ctx, "banana"))
    assert deps.action_sink == []
    assert "not a curated cancer type" in result


def test_set_cancer_type_records_intent_for_known_key():
    deps = _deps()
    ctx = _FakeCtx(deps=deps)
    result = asyncio.run(set_cancer_type(ctx, "breast"))
    assert len(deps.action_sink) == 1
    assert deps.action_sink[0]["action"] == "set_cancer_type"
    assert deps.action_sink[0]["cancer_key"] == "breast"
    assert result  # non-empty


def test_load_example_case_rejects_unknown_id():
    deps = _deps()
    ctx = _FakeCtx(deps=deps)
    result = asyncio.run(load_example_case(ctx, "not_a_real_case"))
    assert deps.action_sink == []
    assert "not a known example case" in result


def test_load_example_case_records_intent_for_known_id():
    deps = _deps()
    ctx = _FakeCtx(deps=deps)
    result = asyncio.run(load_example_case(ctx, "tnbc_aggressive"))
    assert len(deps.action_sink) == 1
    assert deps.action_sink[0] == {"action": "load_case", "case_id": "tnbc_aggressive"}
    assert result


def test_request_tumour_profile_refuses_without_cancer_type():
    deps = _deps(patient_context={})
    ctx = _FakeCtx(deps=deps)
    result = asyncio.run(request_tumour_profile(ctx, "need expression to score"))
    assert deps.action_sink == []
    assert "Set a cancer type first" in result


def test_score_patient_refuses_with_zero_genes():
    deps = _deps(patient_context={"cancer_type": "breast", "model_id": "curated_breast", "genes_provided": 0})
    ctx = _FakeCtx(deps=deps)
    result = asyncio.run(score_patient(ctx))
    assert deps.action_sink == []
    assert "No tumour expression" in result


def test_score_patient_refuses_with_no_model():
    deps = _deps(patient_context={})
    ctx = _FakeCtx(deps=deps)
    result = asyncio.run(score_patient(ctx))
    assert deps.action_sink == []
    assert "No cancer type" in result


def test_score_patient_records_intent_when_ready():
    deps = _deps(patient_context={"cancer_type": "breast", "model_id": "curated_breast", "genes_provided": 50})
    ctx = _FakeCtx(deps=deps)
    result = asyncio.run(score_patient(ctx))
    assert deps.action_sink == [{"action": "score_patient"}]
    assert result


class _FakeEstimate:
    def __init__(self, confidence: float, datasets: int = 8):
        self.confidence_score = confidence
        self.estimated_datasets = datasets
        self.estimated_time_seconds = 180.0
        self.can_proceed = confidence >= 0.5
        self.suggestions = ["name a cancer type", "add a survival outcome"]
        self.improved_query = "gastric cancer overall survival"


class _FakeEstimator:
    def __init__(self, confidence: float | None = 0.85, raises: bool = False):
        self._confidence = confidence
        self._raises = raises
        self.calls: list[str] = []

    async def estimate_query(self, query, user_settings=None, model="mistral"):
        self.calls.append(query)
        if self._raises:
            raise RuntimeError("estimator down")
        return _FakeEstimate(self._confidence)


def test_run_survival_analysis_rejects_empty_query():
    deps = _deps()
    ctx = _FakeCtx(deps=deps)
    result = asyncio.run(run_survival_analysis(ctx, "   "))
    assert deps.action_sink == []
    assert "non-empty query" in result


def test_run_survival_analysis_records_intent_for_a_confident_query():
    estimator = _FakeEstimator(confidence=0.85)
    deps = _deps(estimation_service=estimator)
    ctx = _FakeCtx(deps=deps)

    result = asyncio.run(run_survival_analysis(ctx, "gastric cancer overall survival"))

    assert len(deps.action_sink) == 1
    recorded = deps.action_sink[0]
    assert recorded["action"] == "run_analysis"
    assert recorded["query"] == "gastric cancer overall survival"
    assert recorded["candidate_genes"] is None
    assert recorded["confidence"] == 0.85
    assert recorded["low_confidence"] is False
    assert "confirm" in result.lower()


def test_run_survival_analysis_refuses_a_low_confidence_query():
    # Below 0.4 the run is not even proposed — the agent gets the refinement
    # suggestions back so it can ask a better question instead of burning
    # minutes of GEO downloads on a vague one.
    estimator = _FakeEstimator(confidence=0.2)
    deps = _deps(estimation_service=estimator)
    ctx = _FakeCtx(deps=deps)

    result = asyncio.run(run_survival_analysis(ctx, "cancer genes"))

    assert deps.action_sink == []
    assert "not proposing" in result.lower()
    assert "gastric cancer overall survival" in result


def test_run_survival_analysis_flags_middling_confidence_but_still_proposes():
    estimator = _FakeEstimator(confidence=0.55)
    deps = _deps(estimation_service=estimator)
    ctx = _FakeCtx(deps=deps)

    asyncio.run(run_survival_analysis(ctx, "lung cancer survival"))

    assert deps.action_sink[0]["low_confidence"] is True


def test_run_survival_analysis_uppercases_candidate_genes():
    # candidate_genes is what routes a single-gene question to gene_filter, and
    # therefore what makes its p-values nominal rather than FDR-adjusted.
    estimator = _FakeEstimator(confidence=0.9)
    deps = _deps(estimation_service=estimator)
    ctx = _FakeCtx(deps=deps)

    asyncio.run(run_survival_analysis(ctx, "gastric cancer survival", ["mki67", " tp53 ", ""]))

    assert deps.action_sink[0]["candidate_genes"] == ["MKI67", "TP53"]


def test_run_survival_analysis_fails_open_when_the_estimator_breaks():
    # The user still has to confirm, so a broken estimator must not block the
    # whole workflow.
    deps = _deps(estimation_service=_FakeEstimator(raises=True))
    ctx = _FakeCtx(deps=deps)

    result = asyncio.run(run_survival_analysis(ctx, "gastric cancer overall survival"))

    assert len(deps.action_sink) == 1
    assert deps.action_sink[0]["confidence"] is None
    assert "confirm" in result.lower()


def test_run_survival_analysis_refuses_while_another_run_is_in_flight():
    deps = _deps(estimation_service=_FakeEstimator(), research_context={"analysis_running": True})
    ctx = _FakeCtx(deps=deps)

    result = asyncio.run(run_survival_analysis(ctx, "gastric cancer overall survival"))

    assert deps.action_sink == []
    assert "already running" in result.lower()


# ---------- show_treatment_evidence works without a scored patient ----------

def test_show_treatment_evidence_needs_a_model():
    deps = _deps(patient_context={})
    ctx = _FakeCtx(deps=deps)
    result = asyncio.run(show_treatment_evidence(ctx))
    assert deps.action_sink == []
    assert "no model yet" in result.lower()


def test_show_treatment_evidence_runs_with_a_model_but_no_patient():
    # Tier-1 treated-vs-untreated arms are gene-independent, so requiring a
    # risk_group here used to make this action a silent no-op in research mode.
    deps = _deps(patient_context={"model_id": "curated_breast"})
    ctx = _FakeCtx(deps=deps)

    result = asyncio.run(show_treatment_evidence(ctx))

    assert deps.action_sink == [{"action": "show_treatment_evidence"}]
    assert "not patient-specific" in result.lower()
    assert "observational" in result.lower()


def test_show_treatment_evidence_mentions_the_risk_group_when_scored():
    deps = _deps(patient_context={"model_id": "curated_breast", "risk_group": "high"})
    ctx = _FakeCtx(deps=deps)

    result = asyncio.run(show_treatment_evidence(ctx))

    assert deps.action_sink == [{"action": "show_treatment_evidence"}]
    assert "risk group" in result.lower()


# ---------- get_signature_model_evidence (the one new READ tool) ----------

def test_get_signature_model_evidence_returns_real_provenance():
    service = SignatureService(orchestrator=None)
    model = service.build_demo_signature(max_genes=10)
    deps = _deps(signature_service=service)
    ctx = _FakeCtx(deps=deps)

    result = asyncio.run(get_signature_model_evidence(ctx, model.model_id))

    assert model.training_accession in result
    for cv in model.cohort_validations:
        assert cv.accession in result
    assert "SYNTHETIC DEMO MODEL" in result  # build_demo_signature() always sets is_demo=True


def test_get_signature_model_evidence_unknown_model_id():
    deps = _deps(signature_service=SignatureService(orchestrator=None))
    ctx = _FakeCtx(deps=deps)
    result = asyncio.run(get_signature_model_evidence(ctx, "does-not-exist"))
    assert "No model found" in result


# ---------- Domain Score excludes action tools ----------

def test_action_tool_names_matches_action_tools_list():
    assert ACTION_TOOL_NAMES == {t.__name__ for t in ACTION_TOOLS}


def test_domain_score_ignores_action_tools():
    all_action_calls = ["set_cancer_type", "request_tumour_profile", "score_patient"]
    scoring_tools = [t for t in all_action_calls if t not in ACTION_TOOL_NAMES]
    assert scoring_tools == []
    assert _compute_domain_score(scoring_tools, "no data cited here", None) == 0


def test_domain_score_counts_real_read_tools_after_filtering_actions():
    mixed = ["set_cancer_type", "get_signature_model_evidence", "score_patient"]
    scoring_tools = [t for t in mixed if t not in ACTION_TOOL_NAMES]
    assert scoring_tools == ["get_signature_model_evidence"]
    score = _compute_domain_score(scoring_tools, "Validated on GSE12345 (n=200).", None)
    assert score > 0


# ---------- Tool registry shape ----------

def test_agent_tools_are_the_five_original_plus_one_new_read_tool():
    names = {t.__name__ for t in AGENT_TOOLS}
    assert names == {
        "search_known_datasets",
        "estimate_query",
        "search_geo_datasets",
        "get_gene_info",
        "get_user_recent_results",
        "get_signature_model_evidence",
    }
    assert len(AGENT_TOOLS) == 6


def test_action_tools_count():
    assert len(ACTION_TOOLS) == 12


# ---------- research session block (the no-data half of the workflow) ----------

from app.services.chat.pydantic_ai_service import _build_research_block, _build_settings_block


def test_research_block_reports_that_nothing_has_run():
    block = _build_research_block({})
    assert "No analysis has been run" in block
    # The next step belongs to _build_workflow_block, not here.
    assert "MISSING" not in block


def test_research_block_says_no_patient_data_is_fine():
    # The console has to be usable with nothing loaded; the agent should not be
    # nagging for a tumour profile the question does not need.
    block = _build_research_block({})
    assert "No patient data loaded" in block
    assert "most questions do not need any" in block


def test_research_block_reports_a_run_in_flight():
    block = _build_research_block({"analysis_running": True})
    assert "IN FLIGHT" in block


def test_research_block_flags_a_restricted_run_as_not_fdr_corrected():
    block = _build_research_block({
        "analysis_result_id": "r1", "analysis_query": "gastric",
        "analysis_gene_filter_applied": True,
    })
    assert "NOT multiple-testing corrected" in block
    assert "never FDR q-values" in block


def test_research_block_names_the_last_analysis():
    block = _build_research_block({"analysis_result_id": "r1", "analysis_query": "gastric"})
    assert "gastric" in block and "r1" in block
    assert "MISSING" not in block


def test_research_block_always_carries_the_observational_caveat():
    for ctx in ({}, {"analysis_result_id": "r1"}, {"analysis_running": True}):
        assert "NOT randomised evidence" in _build_research_block(ctx)


def test_settings_block_states_the_hazard_ratio_gates():
    # Without these the agent promises "every gene with p<0.05" while the gates
    # silently drop genes with a significant but small effect.
    block = _build_settings_block({
        "organism": "Homo sapiens", "num_datasets": 20,
        "hazard_ratio_upper": 1.2, "hazard_ratio_lower": 0.8,
    })
    assert "HR >= 1.2 or HR <= 0.8" in block
    assert "NEVER promise" in block


def test_settings_block_omits_the_gates_when_they_are_not_supplied():
    block = _build_settings_block({"organism": "Homo sapiens"})
    assert "Hazard-ratio gates" not in block


# ---------- the single workflow ladder (_build_workflow_block) ----------
#
# The defect this replaces: _build_chart_block and _build_research_block each
# appended their own "MISSING:" line to the SAME system prompt, so with a chart
# open and no analysis run the agent was told to call request_tumour_profile and
# run_survival_analysis at once. The console now derives one ladder
# (frontend/src/utils/caseWorkflow.ts) and sends it; this block renders it.

def test_workflow_block_is_empty_when_the_console_sends_no_workflow():
    # Older clients, and the /research chat, send no workflow fields at all.
    assert _build_workflow_block({}) == ""
    assert _build_workflow_block({"analysis_running": True}) == ""


def test_workflow_block_states_exactly_one_next_step():
    block = _build_workflow_block({
        "workflow_step": "evidence",
        "workflow_done": ["case", "profile"],
        "workflow_next_action": "run_survival_analysis",
    })
    assert block.count("- NEXT:") == 1
    assert "call run_survival_analysis" in block
    assert "[x] Case" in block and "[x] Profile" in block and "[>] Evidence" in block


def test_workflow_block_refuses_the_step_when_it_is_blocked():
    block = _build_workflow_block({
        "workflow_step": "score",
        "workflow_done": ["case"],
        "workflow_next_action": "score_patient",
        "workflow_blocked_reason": "Step 2 (Profile) first — no tumour expression profile has been provided.",
    })
    assert block.count("- NEXT:") == 1
    assert "BLOCKED" in block
    assert "Do not call score_patient" in block


def test_workflow_block_forwards_the_goal_and_its_caveats():
    block = _build_workflow_block({
        "workflow_goal": "treatment",
        "workflow_step": "options",
        "workflow_done": ["case", "profile", "evidence", "score"],
        "workflow_next_action": "show_treatment_evidence",
        "workflow_caveats": ["Synthetic demo model — illustrative only, not evidence about a real cohort."],
    })
    assert "Goal for this session: treatment" in block
    # A caveat the clinician can already see must be repeated, never contradicted.
    assert "Synthetic demo model" in block
    assert "never contradict them" in block


def test_workflow_block_says_nothing_is_left_when_the_goal_is_met():
    block = _build_workflow_block({
        "workflow_step": None,
        "workflow_done": ["case", "evidence"],
        "workflow_goal": "trust",
    })
    assert "NEXT: nothing" in block


# ---------- set_workflow_goal ----------

def test_set_workflow_goal_rejects_a_question_the_app_cannot_answer():
    sink = []
    ctx = _FakeCtx(deps=_deps(action_sink=sink))
    out = asyncio.run(set_workflow_goal(ctx, "cure_the_patient"))
    assert "not a question this app has a pipeline for" in out
    assert sink == []


def test_set_workflow_goal_records_a_known_goal():
    sink = []
    ctx = _FakeCtx(deps=_deps(action_sink=sink))
    out = asyncio.run(set_workflow_goal(ctx, "  Treatment  "))
    assert sink == [{"action": "set_goal", "question_id": "treatment"}]
    assert "treatment" in out


# ---------- refusals quote the console's own sentence ----------

def test_score_patient_quotes_the_consoles_blocked_reason():
    # So the agent tells the clinician exactly what the next-step card says,
    # rather than a second, differently-worded version of the same gate.
    reason = "Step 2 (Profile) first — no tumour expression profile has been provided."
    ctx = _FakeCtx(deps=_deps(
        patient_context={"cancer_type": "breast", "model_id": "m1", "genes_provided": 0},
        research_context={"workflow_blocked_reason": reason},
    ))
    assert asyncio.run(score_patient(ctx)) == reason


def test_score_patient_falls_back_to_its_own_wording_without_a_workflow():
    ctx = _FakeCtx(deps=_deps(
        patient_context={"cancer_type": "breast", "model_id": "m1", "genes_provided": 0},
    ))
    assert "No tumour expression has been provided" in asyncio.run(score_patient(ctx))
