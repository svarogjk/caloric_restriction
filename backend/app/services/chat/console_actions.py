"""
Clinical console workflow ACTION tools.

These tools do not mutate patient data or query real data for the LLM to cite —
they emit *intents* that the browser (which holds the actual expression values
and covariate values) re-validates and executes. The agent proposes a workflow
step ("score this patient", "load the TNBC case"); the browser is the only
thing that ever calls personalizePatient() or reads the pasted expression text.

Excluded from the Domain Score (see ACTION_TOOL_NAMES / _compute_domain_score in
pydantic_ai_service.py) — an action tool orchestrates the UI, it doesn't ground
anything, so counting it would inflate the KPI documented in
.claude/rules/chat_agent.md for free.

Each tool validates what it can against real server state before recording an
intent, so this is not a pure echo of the caller's request:
  - set_cancer_type validates the key against the curated gallery
  - load_example_case validates the case id against the known case catalogue
  - reuse_previous_analysis validates the result_id actually exists
  - score_patient / explain_for_clinician / show_model_quality / etc. refuse
    when the chart doesn't yet have what they need (checked via patient_context)
"""

import logging

from pydantic_ai import RunContext

# A real (non-TYPE_CHECKING) import: pydantic-ai resolves each tool function's
# `ctx: RunContext["AgentDeps"]` forward reference against this module's own
# globals at agent-construction time, so AgentDeps must actually be importable
# here at runtime, not just for type checkers.
from app.services.chat.agent_tools import AgentDeps

logger = logging.getLogger(__name__)

# Mirrors CURATED_CANCERS keys in app/api/gallery_routes.py. Duplicated deliberately
# (small, stable, 6-entry whitelist) rather than importing an API router module
# from a service module — set_cancer_type is scoped to these curated gallery keys
# only; anything else (e.g. "prostate") goes through run_survival_analysis instead.
_CURATED_CANCER_KEYS = frozenset({"breast", "lung", "colorectal", "ovarian", "gastric", "glioma"})

# Mirrors the `id` field of every entry in frontend/src/utils/samplePatients.ts.
_KNOWN_CASE_IDS = frozenset({
    "er_positive_breast", "tnbc_aggressive", "lung_egfr_high", "colorectal_wnt",
    "ovarian_hgsc", "gastric_diffuse", "glioma_idh_wt", "prostate_ar",
})

# Mirrors QuestionId in frontend/src/utils/questionCatalogue.ts — the questions the
# app has a real pipeline for. Duplicated on the same grounds as
# _CURATED_CANCER_KEYS above: a small, stable whitelist is cheaper to keep in sync
# than an import from the UI layer, and validating here is what stops the agent
# inventing a goal that no endpoint serves.
_QUESTION_IDS = frozenset({
    "risk", "drivers", "trust", "treatment", "regimens", "gene", "discovery",
})


def _record(ctx: RunContext["AgentDeps"], action: str, **payload) -> None:
    if ctx.deps.action_sink is not None:
        ctx.deps.action_sink.append({"action": action, **payload})


def _chart(ctx: RunContext["AgentDeps"]) -> dict:
    return ctx.deps.patient_context or {}


def _blocked_reason(ctx: RunContext["AgentDeps"]) -> str | None:
    """The console's own sentence for why the current step cannot run.

    Refusals quote this rather than re-wording it, so the agent tells the
    clinician exactly what the next-step card already says on screen.
    """
    return (ctx.deps.research_context or {}).get("workflow_blocked_reason")


async def set_cancer_type(ctx: RunContext["AgentDeps"], cancer_key: str) -> str:
    """
    Set the active cancer type on the patient chart to one of the curated,
    cross-cohort-validated models (breast, lung, colorectal, ovarian, gastric,
    glioma). For any other cancer type, use run_survival_analysis instead.

    Args:
        cancer_key: One of: breast, lung, colorectal, ovarian, gastric, glioma

    Returns:
        Confirmation with the model's real gene count and discrimination, or a
        refusal if the key isn't a curated cancer type
    """
    key = cancer_key.strip().lower()
    if key not in _CURATED_CANCER_KEYS:
        return (
            f"'{cancer_key}' is not a curated cancer type (curated: "
            f"{', '.join(sorted(_CURATED_CANCER_KEYS))}). Use run_survival_analysis "
            "to build a model for it from live GEO cohorts instead."
        )

    service = ctx.deps.signature_service
    model = service.find_model_by_cancer(key) if service else None
    _record(ctx, "set_cancer_type", cancer_key=key)

    if model is None:
        return f"Cancer type set to {key}, but its curated model isn't ready yet — it's still being prepared."
    demo_note = " (synthetic demo model)" if model.is_demo else ""
    return (
        f"Cancer type set to {key}: model {model.model_id}{demo_note}, "
        f"{len(model.genes)} genes, pooled C-index {model.pooled_c_index:.3f}. "
        "Ask the clinician for the tumour expression profile next."
    )


async def request_tumour_profile(ctx: RunContext["AgentDeps"], reason: str) -> str:
    """
    Ask the clinician to paste or upload the patient's tumour expression profile.
    Call this once a cancer type/model is set and no expression has been provided yet.

    Args:
        reason: One short sentence on why the profile is needed now

    Returns:
        Confirmation that the intake card will be shown
    """
    chart = _chart(ctx)
    if not chart.get("cancer_type") and not chart.get("model_id"):
        return _blocked_reason(ctx) or (
            "Set a cancer type first with set_cancer_type before requesting the tumour profile."
        )
    _record(ctx, "request_expression", reason=reason)
    return "The tumour expression intake card will be shown to the clinician."


async def load_example_case(ctx: RunContext["AgentDeps"], case_id: str) -> str:
    """
    Load one of the built-in synthetic teaching cases (a complete tumour-board
    vignette with cancer type, expression profile, and clinical covariates)
    into the chart. Use this when the clinician asks to see an example or to
    load a specific named case (e.g. "load the TNBC case").

    Args:
        case_id: One of the known case ids, e.g. "tnbc_aggressive", "er_positive_breast"

    Returns:
        Confirmation, or a refusal if the case id is not recognised
    """
    cid = case_id.strip().lower()
    if cid not in _KNOWN_CASE_IDS:
        return f"'{case_id}' is not a known example case. Known cases: {', '.join(sorted(_KNOWN_CASE_IDS))}."
    _record(ctx, "load_case", case_id=cid)
    return f"Loading the '{cid}' example case into the chart. This is synthetic teaching data, not a real patient."


async def score_patient(ctx: RunContext["AgentDeps"]) -> str:
    """
    Score the patient against the active model now that a cancer type and
    tumour expression profile are both set. This is the main workflow action —
    call it as soon as the chart has enough data, don't wait to be asked twice.

    Returns:
        Confirmation, or a refusal explaining what's still missing
    """
    chart = _chart(ctx)
    blocked = _blocked_reason(ctx)
    if not chart.get("model_id") and not chart.get("cancer_type"):
        return blocked or "No cancer type/model set yet — call set_cancer_type or run_survival_analysis first."
    genes_provided = chart.get("genes_provided") or 0
    if genes_provided <= 0:
        return blocked or "No tumour expression has been provided yet — call request_tumour_profile first."
    _record(ctx, "score_patient")
    return "Scoring the patient now — the risk readout will appear in the thread."


async def explain_for_clinician(ctx: RunContext["AgentDeps"]) -> str:
    """
    Show a plain-language clinician summary of the current risk readout.
    Requires the patient to already be scored.

    Returns:
        Confirmation, or a refusal if there's no score yet
    """
    if not _chart(ctx).get("risk_group"):
        return _blocked_reason(ctx) or "The patient hasn't been scored yet — call score_patient first."
    _record(ctx, "explain_for_clinician")
    return "Showing a plain-language summary of this patient's risk readout."


async def show_model_quality(ctx: RunContext["AgentDeps"]) -> str:
    """
    Show the active model's discrimination, nomogram, and concordance benchmark
    against established signatures — for "how good/trustworthy is this model?"
    questions. Requires a model to be set (scoring not required).

    Returns:
        Confirmation, or a refusal if no model is set
    """
    if not _chart(ctx).get("model_id"):
        return _blocked_reason(ctx) or "No model is set yet — call set_cancer_type or run_survival_analysis first."
    _record(ctx, "show_model_quality")
    return "Showing the model's discrimination, nomogram, and concordance benchmark."


async def show_treatment_evidence(ctx: RunContext["AgentDeps"]) -> str:
    """
    Show documented treatment evidence for the current model: biomarker-to-therapy
    records plus observational treated-vs-untreated survival curves from the
    model's own GEO cohort.

    Works WITHOUT a tumour profile — the treated-vs-untreated arms are
    gene-independent. With a scored patient it can additionally pick the
    comparable risk group in each treatment-matched cohort.

    Returns:
        Confirmation that the treatment evidence panel was opened.
    """
    chart = _chart(ctx)
    if not chart.get("model_id"):
        return (
            "There is no model yet. Run an analysis (run_survival_analysis) or pick a "
            "curated cancer type first — treatment evidence is looked up per model."
        )
    _record(ctx, "show_treatment_evidence")
    if chart.get("risk_group"):
        return (
            "Opening treatment evidence, including this patient's comparable risk group "
            "in each treatment-matched cohort. Advisory and research-use-only."
        )
    return (
        "Opening treatment evidence for this model's cohorts. Without a tumour profile these "
        "are cohort-level treated-vs-untreated curves, not patient-specific predictions — and "
        "they are observational, not randomised. Advisory and research-use-only."
    )


async def show_treatment_context(ctx: RunContext["AgentDeps"]) -> str:
    """
    Show outcomes across documented treatment cohorts for this cancer type
    (F24) — separate from the biomarker-evidence view, this compares whole
    treatment regimens. Requires a cancer type to be set.

    Returns:
        Confirmation, or a refusal if no cancer type is set
    """
    if not _chart(ctx).get("cancer_type"):
        return _blocked_reason(ctx) or "No cancer type is set yet — call set_cancer_type first."
    _record(ctx, "show_treatment_context")
    return "Showing outcomes across documented treatment cohorts for this cancer type."


async def show_driver_biology(ctx: RunContext["AgentDeps"]) -> str:
    """
    Show pathway/GO enrichment for this patient's risk-driving genes — the
    biological programme behind the score, not just the gene list.
    Requires the patient to already be scored.

    Returns:
        Confirmation, or a refusal if there's no score yet
    """
    if not _chart(ctx).get("risk_group"):
        return _blocked_reason(ctx) or "The patient hasn't been scored yet — call score_patient first."
    _record(ctx, "show_driver_biology")
    return "Showing pathway enrichment for this patient's risk-driving genes."


async def reuse_previous_analysis(ctx: RunContext["AgentDeps"], result_id: str) -> str:
    """
    Reuse a previously saved cross-cohort analysis to score this patient,
    instead of spending 2-5 minutes rebuilding one. Call get_user_recent_results
    first to find a candidate result_id.

    Args:
        result_id: A saved analysis result id from the clinician's history

    Returns:
        Confirmation, or a refusal if the result can't be found
    """
    db = ctx.deps.db_session
    if db is None:
        return "No database session available to look up that result."
    try:
        from app.services.analysis_result_service import analysis_result_service

        record = await analysis_result_service.get_result(db, result_id)
    except (AttributeError, KeyError, ValueError) as exc:
        logger.warning(f"reuse_previous_analysis lookup failed for {result_id}: {exc}")
        return f"Could not look up that result: {exc}"

    if record is None:
        return f"No saved analysis found with id '{result_id}'."
    _record(ctx, "reuse_previous_analysis", result_id=result_id)
    n_genes = len(record.get("common_genes", []))
    return f"Reusing the saved analysis '{record.get('query', result_id)}' ({n_genes} genes) to score this patient."


async def run_survival_analysis(
    ctx: RunContext["AgentDeps"],
    query: str,
    candidate_genes: list[str] | None = None,
) -> str:
    """
    Run a real cross-cohort survival analysis over live NCBI GEO cohorts: Cox
    regression and log-rank tests per dataset, ranked by cross-cohort
    consistency. Takes 2-5 minutes. Works with or without a patient chart.

    This PROPOSES the run — the user confirms with one click before anything
    starts. Query confidence is checked here, so a vague query is refused and
    returned to you for refinement rather than burning minutes of downloads.

    Args:
        query: The survival analysis query, e.g. "gastric cancer overall survival".
        candidate_genes: Restrict the analysis to these gene symbols. Pass them
            when the question is about specific named genes ("does high MKI67
            predict worse survival?"). This makes the run far cheaper, but it
            also means only those genes are tested — so the resulting p-values
            are NOT multiple-testing corrected, and the app will label them as
            nominal rather than FDR-adjusted. Leave empty for open-ended
            discovery ("which genes predict survival in ...").

    Returns:
        Either a refusal with refinement suggestions, or confirmation that a
        proposal was shown to the user.
    """
    q = query.strip()
    if not q:
        return "A non-empty query is required, e.g. 'gastric cancer overall survival'."

    research = ctx.deps.research_context or {}
    if research.get("analysis_running"):
        return (
            "An analysis is already running. Wait for it to finish, or answer from the "
            "current results — starting a second one is refused."
        )

    genes = [g.strip().upper() for g in (candidate_genes or []) if g and g.strip()]

    # Confidence gate. Thresholds match .claude/rules/chat-system.md:
    # >=0.7 proceed, 0.4-0.7 proceed but flag, <0.4 refuse and refine.
    confidence: float | None = None
    estimated_datasets: int | None = None
    estimated_seconds: float | None = None
    try:
        estimate = await ctx.deps.estimation_service.estimate_query(
            q, user_settings=ctx.deps.user_settings, model=ctx.deps.model
        )
        confidence = estimate.confidence_score
        estimated_datasets = estimate.estimated_datasets
        estimated_seconds = estimate.estimated_time_seconds

        if confidence < 0.4:
            lines = [
                f"Not proposing a run for '{q}' — confidence is only {confidence:.0%}, "
                f"with about {estimated_datasets} usable datasets expected.",
            ]
            if estimate.suggestions:
                lines.append("Refine it: " + "; ".join(estimate.suggestions[:3]))
            if estimate.improved_query:
                lines.append(f"Try instead: '{estimate.improved_query}'")
            lines.append("Call run_survival_analysis again with a better query.")
            return " ".join(lines)
    except (AttributeError, KeyError, ValueError, TypeError, RuntimeError) as exc:
        # Fail open: the user still has to confirm, so a broken estimator must
        # not block the whole workflow. Recorded with confidence=None.
        logger.warning("estimate_query failed inside run_survival_analysis: %s", exc)

    _record(
        ctx,
        "run_analysis",
        query=q,
        candidate_genes=genes or None,
        confidence=confidence,
        estimated_datasets=estimated_datasets,
        estimated_time_seconds=estimated_seconds,
        low_confidence=confidence is not None and confidence < 0.7,
    )

    parts = [f"Proposing a cross-cohort survival analysis for '{q}'"]
    if genes:
        parts.append(f"restricted to {', '.join(genes)}")
    if confidence is not None:
        parts.append(f"— confidence {confidence:.0%}, about {estimated_datasets} datasets")
    parts.append("(2-5 minutes). The user must confirm before it starts.")
    return " ".join(parts)


async def set_workflow_goal(ctx: RunContext["AgentDeps"], question_id: str) -> str:
    """
    Record which of the app's answerable questions this session is pursuing.
    Call this as soon as the clinician's intent is clear — it scopes the
    workflow, so steps the question does not need stop being reported as
    missing.

    Args:
        question_id: One of: risk, drivers, trust, treatment, regimens, gene,
            discovery. See the "What this app can actually answer" list.

    Returns:
        Confirmation, or a refusal naming the valid goals
    """
    qid = question_id.strip().lower()
    if qid not in _QUESTION_IDS:
        return (
            f"'{question_id}' is not a question this app has a pipeline for. Valid goals: "
            f"{', '.join(sorted(_QUESTION_IDS))}. If the clinician wants something else, say "
            "plainly that there is no computation for it rather than setting a goal."
        )
    _record(ctx, "set_goal", question_id=qid)
    return (
        f"Goal set to '{qid}'. The Workflow block now lists only the steps this question "
        "needs — follow its NEXT line."
    )


# Tool names excluded from the Domain Score — see pydantic_ai_service.py._compute_domain_score.
ACTION_TOOL_NAMES = frozenset({
    "set_workflow_goal",
    "set_cancer_type",
    "request_tumour_profile",
    "load_example_case",
    "score_patient",
    "explain_for_clinician",
    "show_model_quality",
    "show_treatment_evidence",
    "show_treatment_context",
    "show_driver_biology",
    "reuse_previous_analysis",
    "run_survival_analysis",
})

ACTION_TOOLS = [
    set_workflow_goal,
    set_cancer_type,
    request_tumour_profile,
    load_example_case,
    score_patient,
    explain_for_clinician,
    show_model_quality,
    show_treatment_evidence,
    show_treatment_context,
    show_driver_biology,
    reuse_previous_analysis,
    run_survival_analysis,
]
