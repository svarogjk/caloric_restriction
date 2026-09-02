"""
PydanticAI Service for conversational AI.

Uses PydanticAI Agent with tool-calling support and clean streaming via run_stream().

History management:
- Per-conversation history is maintained externally in PostgreSQL (ConversationService)
- Before passing to the agent, old messages are trimmed once the estimated token count
  exceeds 4000 tokens (~16,000 chars)
"""

import logging
import os
import re
from pathlib import Path
from typing import AsyncGenerator

from pydantic_ai import Agent, RunContext
from pydantic_ai.models.mistral import MistralModel
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.providers.mistral import MistralProvider
from pydantic_ai.providers.anthropic import AnthropicProvider
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    UserPromptPart,
    TextPart,
)

from app.services.chat.agent_tools import AgentDeps, AGENT_TOOLS
from app.services.chat.console_actions import ACTION_TOOLS, ACTION_TOOL_NAMES

logger = logging.getLogger(__name__)

# Path to optional key files (relative to services directory)
SERVICES_DIR = Path(__file__).parent.parent

# ~4 chars per token; trim to 4000 token budget ≈ 16,000 chars
_MAX_HISTORY_CHARS = 16_000

# Domain Score patterns — compiled once at module level
_GSE_PATTERN = re.compile(r'GSE\d+')
_STATS_PATTERN = re.compile(
    r'(HR\s*[=:><!]|hazard ratio|p\s*[=<>]\s*0\.\d+|\d+\s+samples?|\bCI\b|\bconfidence interval\b)',
    re.IGNORECASE,
)

_BASE_SYSTEM_PROMPT = """You are a domain-specific bioinformatics assistant for GEO Survival Analysis. Your answers must come from REAL GEO data — call tools to search datasets, cite GSE accession IDs, and quote actual hazard ratios. A response that could have come from ChatGPT without this app's tools has zero value.

## Tools (call on every substantive question)
- **search_known_datasets**: semantic search over indexed local GEO datasets — call first for "do we have X data?" questions
- **estimate_query**: pre-flight confidence check; call before suggesting a run
- **search_geo_datasets**: live NCBI GEO search to show available cohorts
- **get_gene_info**: NCBI Entrez gene summary for function and disease associations
- **get_user_recent_results**: user's analysis history — call when asked "what have I analyzed before?"
- **get_signature_model_evidence**: real cohort provenance (GSE accessions, per-cohort C-index) for a prognostic model — call when asked what a risk score is based on

## Console workflow tools
These orchestrate the UI — they never see or touch patient data. Use them to drive
the workflow instead of asking the user to click through the app by hand:
**run_survival_analysis, reuse_previous_analysis, set_cancer_type,
request_tumour_profile, load_example_case, score_patient, explain_for_clinician,
show_model_quality, show_treatment_evidence, show_treatment_context,
show_driver_biology**.

Some need a patient chart and some do not — run_survival_analysis,
reuse_previous_analysis, show_model_quality and show_treatment_evidence all work
with no patient data at all. The "Research session" and "Active patient chart"
blocks below say what is already set; the "Workflow" block says what to do next,
and it is the ONLY place that says so.

## What this app can actually answer
Every question the console can compute an answer to maps onto one of these, and
each one runs real computation over GEO cohorts — never your own recall:
- **risk** — how high is this patient's risk (risk group, percentile, C-index)
- **drivers** — which genes drive that score, and their pathway enrichment
- **trust** — the model's training/validation cohorts, per-cohort C-index, nomogram, concordance
- **treatment** — documented biomarker-to-therapy evidence (CIViC/DGIdb) for this profile
- **regimens** — outcomes across documented treatment cohorts for this cancer type
- **gene** — is a named gene prognostic or predictive here (per-cohort HR + interaction test)
- **discovery** — which genes predict survival in a cancer type, ranked by cross-cohort consistency

If a question falls outside all of these, say plainly that the app has no
computation for it, answer only from what tools return or what is already on
screen, and offer the nearest one of the above. Never invent a capability.

## Response Standards
- Every dataset reference must include its GSE accession (e.g. GSE12345, GSE67890)
- Every hazard ratio claim must name the dataset it came from
- Generic advice without data citations is unacceptable
- To run an analysis, call **run_survival_analysis**. It PROPOSES the run and the user confirms with one click — never tell someone to click a button you can call yourself
- For a question about specific named genes, pass them as `candidate_genes`. Those results are then NOT multiple-testing corrected, so call the p-value "nominal", never an FDR q-value
- NEVER describe results from a run that has not completed. Wait for the analysis to appear

## Key Statistics
- HR > 1: high expression = worse survival (oncogenic marker)
- HR < 1: high expression = protective
- Log-rank p < 0.05 = statistically significant survival difference
- I² > 50% = substantial heterogeneity across datasets
- Predictive (treatment-effect-modifying) biomarker = its survival effect DIFFERS by treatment arm (significant expression×treatment interaction p); contrast with a purely prognostic gene whose effect is treatment-independent

## Positioning
- Treatment guidance is ADVISORY and hypothesis-generating — "treatments to consider/discuss", grounded in documented evidence; never a prescription or a guarantee of response. Research use only."""


def _build_research_block(research: dict) -> str:
    """Session state with no patient involved: is a run in flight, what did the
    last one produce, and what is the next step. This is what makes the console
    usable with nothing loaded — without it the agent has no idea whether an
    analysis exists."""
    lines = ["\n## Research session"]

    if research.get("analysis_running"):
        lines.append("- An analysis is IN FLIGHT right now")

    result_id = research.get("analysis_result_id")
    if result_id:
        lines.append(f"- Last analysis: '{research.get('analysis_query')}' (result {result_id})")
        n_genes = research.get("analysis_n_genes")
        n_datasets = research.get("analysis_n_datasets")
        if n_genes is not None and n_datasets is not None:
            lines.append(f"  - {n_genes} genes across {n_datasets} cohorts")
        top = research.get("analysis_top_genes") or []
        if top:
            lines.append(f"  - Top genes: {', '.join(top)}")
        n_pred = research.get("analysis_n_predictive_genes")
        if n_pred:
            lines.append(f"  - {n_pred} are treatment-effect-modifying (predictive)")
        if research.get("analysis_gene_filter_applied"):
            lines.append(
                "  - RESTRICTED to named candidate genes, so its p-values are NOT "
                "multiple-testing corrected. Call them nominal p-values, never FDR q-values"
            )
        if research.get("analysis_model_id"):
            lines.append(f"  - Signature model ready: {research['analysis_model_id']}")
    else:
        lines.append("- No analysis has been run in this session yet")

    if research.get("has_patient_chart"):
        pasted = research.get("expression_genes_pasted")
        lines.append(f"- A patient chart is open ({pasted or 0} genes pasted)")
    else:
        lines.append("- No patient data loaded — this is fine, most questions do not need any")

    # The "what next" ladder deliberately does NOT live here — see
    # _build_workflow_block. Two independently-derived ladders (this one and the
    # chart block's) used to contradict each other in the same prompt.

    lines.append(
        "\nObservational treated-vs-untreated curves are NOT randomised evidence. Treatment "
        "assignment reasons are unknown and may fully explain any difference. Always say so."
    )
    return "\n".join(lines)


# Mirrors WORKFLOW_STEP_IDS / SPECS in frontend/src/utils/caseWorkflow.ts. Only
# the labels and the tool mapping are duplicated (small and stable); the STATE is
# always sent from the browser, never re-derived here — one derivation, one truth.
_WORKFLOW_STEPS: list[tuple[str, str, str]] = [
    ("case", "Case", "set_cancer_type"),
    ("profile", "Profile", "request_tumour_profile"),
    ("evidence", "Evidence", "run_survival_analysis"),
    ("score", "Score", "score_patient"),
    ("why", "Why", "show_model_quality"),
    ("options", "Options", "show_treatment_evidence"),
]


def _build_workflow_block(research: dict) -> str:
    """The ONE next-step ladder.

    The console derives the whole pipeline from the state the clinician can see
    (frontend/src/utils/caseWorkflow.ts) and sends the result. Rendering it here
    rather than recomputing it means the agent's "what next" and the clinician's
    on-screen "what next" cannot disagree — which they did, routinely, when the
    chart block and the research block each appended their own MISSING line.
    """
    step = research.get("workflow_step")
    if not step and not research.get("workflow_done"):
        return ""

    done = set(research.get("workflow_done") or [])
    goal = research.get("workflow_goal")

    lines = ["\n## Workflow (the single source of what to do next)"]
    if goal:
        lines.append(f"- Goal for this session: {goal}")

    for step_id, label, _tool in _WORKFLOW_STEPS:
        if step_id in done:
            mark = "[x]"
        elif step_id == step:
            mark = "[>]"
        else:
            mark = "[ ]"
        lines.append(f"  {mark} {label}")

    caveats = research.get("workflow_caveats") or []
    if caveats:
        lines.append("- Limitations ALREADY shown to the clinician — repeat them, never contradict them:")
        for c in caveats:
            lines.append(f"  - {c}")

    if step:
        tool = research.get("workflow_next_action")
        blocked = research.get("workflow_blocked_reason")
        if blocked:
            lines.append(
                f"- NEXT: '{step}' is BLOCKED — {blocked} Do not call {tool or 'its tool'}; "
                "say what is needed and drive the earlier step instead."
            )
        else:
            lines.append(
                f"- NEXT: call {tool} to advance the '{step}' step. This is the only next "
                "step — do not propose a different one, and do not ask the clinician to do "
                "by hand what this tool does."
            )
    else:
        lines.append("- NEXT: nothing. Every step this goal needs has run — answer from what is on screen.")

    lines.append(
        "- Steps marked [ ] that come AFTER the current one are not yet reachable. Never "
        "describe their output as if it existed."
    )
    return "\n".join(lines)


def _build_settings_block(user_settings: dict) -> str:
    """Build the dynamic settings section appended to the system prompt per-request."""
    organism = user_settings.get("organism") or "any organism"
    cancer_only = user_settings.get("cancer_genes_only", False)
    n_datasets = user_settings.get("num_datasets", 10)
    genes = user_settings.get("candidate_genes") or []

    lines = ["\n## Active User Configuration (ALREADY SET — do NOT re-suggest these)"]
    lines.append(f"- Organism: {organism}")
    if cancer_only:
        lines.append("- Cancer genes only: True → analysis is RESTRICTED to ~600 COSMIC driver genes")
    else:
        lines.append("- Cancer genes only: False → genome-wide analysis")
    lines.append(f"- Max datasets to analyze: {n_datasets}")

    if genes:
        genes_str = ", ".join(genes[:10])
        if len(genes) > 10:
            genes_str += f" … ({len(genes)} total)"
        lines.append(f"- Candidate genes: {genes_str} (analysis restricted to this list)")
    elif cancer_only:
        lines.append("- Candidate genes: COSMIC cancer driver list (~600 genes) — NOT genome-wide")
    else:
        lines.append("- Candidate genes: none — genome-wide analysis across all expressed genes")

    # Explicit constraints derived from settings
    lines.append("\n## Constraints from user settings (state these accurately, never contradict):")
    if cancer_only and not genes:
        lines.append("- NEVER say 'test all ~20,000 genes' or 'genome-wide' — the user has restricted to ~600 COSMIC genes")
    if genes:
        lines.append(f"- NEVER suggest a genome-wide run — the user has {len(genes)} candidate genes pre-selected")
    hr_upper = user_settings.get("hazard_ratio_upper")
    hr_lower = user_settings.get("hazard_ratio_lower")
    if hr_upper is not None and hr_lower is not None:
        lines.append(
            f"- Hazard-ratio gates: a gene must have HR >= {hr_upper} or HR <= {hr_lower} to be "
            "reported, ON TOP of the p-value threshold. NEVER promise 'every gene with p<0.05' — "
            "genes with a significant but small effect are excluded by these gates"
        )
    lines.append(
        f"- When calling search_geo_datasets or get_gene_info, use organism='{organism}' "
        "unless the user explicitly overrides it in their message"
    )
    return "\n".join(lines)


def _build_chart_block(patient_context: dict) -> str:
    """Build the dynamic clinical-console chart-state block appended to the
    system prompt per-request. Renders only the fields that are set, and always
    states what's still missing so the agent knows the next workflow step —
    drive it with an ACTION tool (console_actions.py) rather than asking the
    clinician to do by hand what an action tool can do."""
    lines = ["\n## Active patient chart (de-identified — the clinician has this on screen)"]
    lines.append("You are running the workflow for a clinician with ONE patient's chart open.")

    cancer_type = patient_context.get("cancer_type")
    model_id = patient_context.get("model_id")
    genes_provided = patient_context.get("genes_provided") or 0
    risk_group = patient_context.get("risk_group")

    if cancer_type or model_id:
        demo_note = " (synthetic demo model)" if patient_context.get("model_is_demo") else ""
        lines.append(f"- Cancer type: {cancer_type or 'set'}{demo_note}" + (f" (model {model_id})" if model_id else ""))
    if genes_provided:
        matched = patient_context.get("genes_used")
        total = patient_context.get("genes_total")
        coverage = f" · {matched} of {total} signature genes matched" if matched is not None and total else ""
        lines.append(f"- Tumour profile: {genes_provided} genes provided{coverage}")
    if patient_context.get("clinical_covariate_names"):
        lines.append(
            "- Clinical covariates supplied: " + ", ".join(patient_context["clinical_covariate_names"])
            + "   (values NOT transmitted)"
        )
    if risk_group:
        pct = patient_context.get("risk_percentile")
        scored_on = patient_context.get("scored_on")
        lines.append(
            f"- Score: {risk_group.upper()} risk"
            + (f", {pct:.0f}th percentile" if pct is not None else "")
            + (f", scored on {scored_on}" if scored_on else "")
        )
    if patient_context.get("pooled_c_index") is not None or patient_context.get("c_index_combined") is not None:
        c_combined = patient_context.get("c_index_combined")
        delta = patient_context.get("delta_c_index")
        lines.append(
            f"- Discrimination: pooled C-index {patient_context.get('pooled_c_index', c_combined):.3f}"
            + (f" (combined {c_combined:.3f}, Δ {delta:+.3f} over expression)" if c_combined is not None and delta is not None else "")
        )
    if patient_context.get("top_risk_genes"):
        lines.append("- Top risk-increasing genes: " + ", ".join(patient_context["top_risk_genes"]))
    if patient_context.get("top_protective_genes"):
        lines.append("- Top protective genes: " + ", ".join(patient_context["top_protective_genes"]))
    if patient_context.get("warnings"):
        lines.append("- Model warnings: " + "; ".join(patient_context["warnings"]))

    # No MISSING line here — the Workflow section is the single ladder.

    lines.append(
        "\nWorkflow rules:\n"
        "- Drive the next step with an action tool. Never ask the clinician to do by hand\n"
        "  what an action tool can do.\n"
        "- Ground every claim in real GEO data — call a read tool and cite GSE accessions.\n"
        "- Before proposing a 2-5 minute cohort build, call estimate_query first and report\n"
        "  the confidence and dataset count. Check get_user_recent_results and\n"
        "  search_known_datasets before spending the clinician's time on a new run.\n"
        "- These figures are already computed and on screen. Never recompute or invent numbers.\n"
        "- You cannot see the patient's identity, expression values, or clinical values.\n"
        "  Never claim otherwise and never ask for identifying details.\n"
        "- Never give a prescription, a dose, or a claim that this patient will respond.\n"
        "  Treatment talk is advisory: \"worth discussing with the tumour board\".\n"
        "- A single-sample estimate is uncertain — say so when the answer turns on it."
    )
    return "\n".join(lines)


def _compute_domain_score(
    tools_invoked: list[str],
    response_text: str,
    user_settings: dict | None,
) -> int:
    """
    Compute a 0-100 score measuring how domain-specific this response is vs. generic ChatGPT.

    Components:
    - Tool invocations: +20 each, max 40 (proves real data was queried)
    - GSE citations: +15 each, max 30 (ChatGPT has no live GEO access)
    - Statistical values (HR, p-value, n= samples): +15 if any found
    - Settings integration (organism/genes referenced): +15 if any found

    Zero = could be ChatGPT. 100 = deeply grounded in real domain data.
    """
    score = 0

    # Tool usage (0–40 pts)
    score += min(len(tools_invoked) * 20, 40)

    # Dataset citations (0–30 pts)
    gse_count = len(_GSE_PATTERN.findall(response_text))
    score += min(gse_count * 15, 30)

    # Statistical values (0–15 pts)
    if _STATS_PATTERN.search(response_text):
        score += 15

    # Settings integration (0–15 pts)
    if user_settings:
        organism = (user_settings.get("organism") or "").lower()
        genes = [g.lower() for g in (user_settings.get("candidate_genes") or [])]
        text_lower = response_text.lower()
        if (organism and organism in text_lower) or any(g in text_lower for g in genes[:5]):
            score += 15

    return min(score, 100)


class PydanticAIService:
    """Service for PydanticAI-based conversations with tool-calling support."""

    def __init__(self) -> None:
        self._models = self._init_models()
        self._agents: dict[str, Agent] = {}
        self._deps: AgentDeps | None = None

    # ------------------------------------------------------------------
    # Dependency injection
    # ------------------------------------------------------------------

    def set_deps(self, deps: AgentDeps) -> None:
        """
        Inject service dependencies used by agent tools.

        Call once at startup after all services are ready.
        Invalidates cached agents so they are rebuilt with fresh deps.
        """
        self._deps = deps
        self._agents = {}
        logger.info("AgentDeps injected; agents will be rebuilt on first use")

    # ------------------------------------------------------------------
    # Model initialisation
    # ------------------------------------------------------------------

    def _init_models(self) -> dict:
        models: dict = {}

        mistral_key = os.getenv("MISTRAL_KEY")
        if not mistral_key:
            key_file = SERVICES_DIR / "mistral_key.txt"
            if key_file.exists():
                mistral_key = key_file.read_text().strip()
                logger.info("Loaded Mistral key from file")

        if mistral_key:
            models["mistral"] = MistralModel(
                "mistral-small-latest",
                provider=MistralProvider(api_key=mistral_key),
            )
            logger.info("Initialized Mistral Small model")

            models["mistral-large"] = MistralModel(
                "mistral-large-latest",
                provider=MistralProvider(api_key=mistral_key),
            )
            logger.info("Initialized Mistral Large model")

        anthropic_key = os.getenv("ANTHROPIC_KEY")
        if not anthropic_key:
            key_file = SERVICES_DIR / "anthropic_key.txt"
            if key_file.exists():
                anthropic_key = key_file.read_text().strip()
                logger.info("Loaded Anthropic key from file")

        if anthropic_key:
            models["anthropic"] = AnthropicModel(
                "claude-haiku-4-5-20251001",
                provider=AnthropicProvider(api_key=anthropic_key),
            )
            logger.info("Initialized Anthropic model")

        if not models:
            logger.warning("No LLM models configured — check API keys")

        return models

    # ------------------------------------------------------------------
    # Agent creation
    # ------------------------------------------------------------------

    def _get_agent(self, model_name: str) -> "Agent[AgentDeps, str]":
        """Get or create a PydanticAI Agent for the given model."""
        if model_name in self._agents:
            return self._agents[model_name]

        if model_name not in self._models:
            raise ValueError(f"Model '{model_name}' not available")

        agent: Agent[AgentDeps, str] = Agent(
            self._models[model_name],
            deps_type=AgentDeps,
            system_prompt=_BASE_SYSTEM_PROMPT,
            tools=AGENT_TOOLS + ACTION_TOOLS,
            # Mistral (and others) sometimes emit final text AND a tool call in the
            # same step. pydantic-ai's default 'early' strategy treats the text as
            # the final result and silently SKIPS the tool call — the function body
            # never runs (confirmed: ToolReturnPart "Tool not executed - a final
            # result was already processed"). That's exactly the class of silent
            # tool-skip .claude/rules/chat_agent.md warns against, and it means a
            # console action tool's whole point (recording an intent in
            # action_sink) never happens. 'exhaustive' always runs requested tools.
            end_strategy='exhaustive',
        )

        # Dynamic per-request settings block — reads ctx.deps at run time
        @agent.system_prompt
        async def _settings_prompt(ctx: RunContext[AgentDeps]) -> str:
            if ctx.deps.user_settings:
                return _build_settings_block(ctx.deps.user_settings)
            return ""

        # Dynamic per-request clinical-console chart state — registered
        # separately from _settings_prompt since it's independent context
        # (a clinician chart vs. a researcher's analysis settings).
        @agent.system_prompt
        async def _chart_prompt(ctx: RunContext[AgentDeps]) -> str:
            if ctx.deps.patient_context:
                return _build_chart_block(ctx.deps.patient_context)
            return ""

        # Dynamic per-request research-session state. Unlike the chart block this
        # applies with no patient data at all, which is the case the console has
        # to support first.
        @agent.system_prompt
        async def _research_prompt(ctx: RunContext[AgentDeps]) -> str:
            if ctx.deps.research_context:
                return _build_research_block(ctx.deps.research_context)
            return ""

        # The single next-step ladder, derived in the browser and forwarded. Kept
        # separate from _research_prompt so the facts about the session and the
        # instruction about what to do next stay independently reviewable.
        @agent.system_prompt
        async def _workflow_prompt(ctx: RunContext[AgentDeps]) -> str:
            if ctx.deps.research_context:
                return _build_workflow_block(ctx.deps.research_context)
            return ""

        self._agents[model_name] = agent
        logger.info(
            f"Created agent for model '{model_name}' with {len(AGENT_TOOLS) + len(ACTION_TOOLS)} tools"
        )
        return agent

    # ------------------------------------------------------------------
    # History helpers
    # ------------------------------------------------------------------

    def _convert_history(self, messages: list[dict]) -> list[ModelMessage]:
        """Convert DB dict messages to PydanticAI ModelMessage objects."""
        result: list[ModelMessage] = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "user":
                result.append(ModelRequest(parts=[UserPromptPart(content=content)]))
            elif role == "assistant":
                result.append(ModelResponse(parts=[TextPart(content=content)]))
            # system messages are handled via system_prompt parameter — skip here
        return result

    def _trim_history(self, messages: list[ModelMessage]) -> list[ModelMessage]:
        """
        Trim history to fit within the context budget.

        Drops oldest messages until total character count is within
        _MAX_HISTORY_CHARS. Ensures history starts with a user (ModelRequest) message.
        """
        def _char_count(msgs: list[ModelMessage]) -> int:
            total = 0
            for m in msgs:
                for part in m.parts:
                    if hasattr(part, "content") and isinstance(part.content, str):
                        total += len(part.content)
            return total

        if _char_count(messages) <= _MAX_HISTORY_CHARS:
            return messages

        # Drop oldest messages until within budget
        while messages and _char_count(messages) > _MAX_HISTORY_CHARS:
            messages = messages[1:]

        # History should start with a user message
        while messages and not isinstance(messages[0], ModelRequest):
            messages = messages[1:]

        return messages

    def _build_context_note(self, estimation_context: dict) -> str:
        """Append query estimation data to the user message."""
        confidence = estimation_context.get("confidence_score", 0)
        suggestions = estimation_context.get("suggestions", [])
        geo_preview = estimation_context.get("geo_preview")

        note = f"\n\n[Query Analysis: {confidence:.0%} confidence"

        if geo_preview:
            total = geo_preview.get("total_datasets", 0)
            survival_count = geo_preview.get("datasets_with_survival_keywords", 0)
            note += f", Found {total} datasets ({survival_count} with survival data)"
            warnings = geo_preview.get("warnings", [])
            if warnings:
                note += f", Warnings: {warnings[0][:50]}..."

        if suggestions:
            note += f", Suggestions: {'; '.join(suggestions[:2])}"
        note += "]"
        return note

    # ------------------------------------------------------------------
    # Metrics extraction helper
    # ------------------------------------------------------------------

    def _extract_tool_names(self, messages: list[ModelMessage]) -> list[str]:
        """Extract tool names called during this run from new messages."""
        tools: list[str] = []
        for msg in messages:
            for part in getattr(msg, "parts", []):
                if hasattr(part, "tool_name"):
                    tools.append(part.tool_name)
        return tools

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def generate_response(
        self,
        messages: list[dict],
        model: str = "mistral-large",
        estimation_context: dict | None = None,
        conversation_id: str | None = None,
        deps_override: AgentDeps | None = None,
    ) -> tuple[str, int | None, int]:
        """
        Generate a complete (non-streaming) response.

        Args:
            messages: Full conversation history as dicts with 'role'/'content'
            model: Model name ('mistral', 'mistral-large', or 'anthropic')
            estimation_context: Optional pre-flight estimation data
            conversation_id: Used for metrics logging
            deps_override: Per-request AgentDeps with user_settings/user_id

        Returns:
            Tuple of (response text, tokens used or None, domain_score 0-100)
        """
        if not messages:
            return "Hello! How can I help you with survival analysis today?", None, 0

        user_content = messages[-1].get("content", "")
        if estimation_context:
            user_content += self._build_context_note(estimation_context)

        history = self._trim_history(self._convert_history(messages[:-1]))

        deps = deps_override if deps_override is not None else self._deps
        agent = self._get_agent(model)
        result = await agent.run(
            user_content,
            message_history=history,
            deps=deps,
        )

        tools_invoked = self._extract_tool_names(result.new_messages())
        user_settings = deps_override.user_settings if deps_override else None
        # Action tools (console_actions.py) orchestrate the UI — they query nothing,
        # so they're excluded from the Domain Score. tools_invoked keeps the full
        # list for logging/transparency.
        scoring_tools = [t for t in tools_invoked if t not in ACTION_TOOL_NAMES]
        domain_score = _compute_domain_score(scoring_tools, result.output, user_settings)

        logger.info(
            "chat_metrics conversation_id=%s tools=%s gse_citations=%d domain_score=%d",
            conversation_id,
            tools_invoked,
            len(_GSE_PATTERN.findall(result.output)),
            domain_score,
        )

        return result.output, None, domain_score

    async def stream_response(
        self,
        messages: list[dict],
        model: str = "mistral-large",
        estimation_context: dict | None = None,
        conversation_id: str | None = None,
        deps_override: AgentDeps | None = None,
        result_sink: dict | None = None,
    ) -> AsyncGenerator[str, None]:
        """
        Stream response tokens via PydanticAI run_stream.

        Yields text deltas directly. After exhaustion, populates result_sink with:
        - "tools": list of tool names called
        - "domain_score": int 0-100

        Args:
            messages: Full conversation history
            model: Model name
            estimation_context: Optional pre-flight estimation data
            conversation_id: Used for metrics logging
            deps_override: Per-request AgentDeps with user_settings/user_id
            result_sink: Mutable dict populated with metrics after streaming completes

        Yields:
            Response text chunks as they are generated
        """
        if not messages:
            yield "Hello! How can I help you with survival analysis today?"
            return

        user_content = messages[-1].get("content", "")
        if estimation_context:
            user_content += self._build_context_note(estimation_context)

        history = self._trim_history(self._convert_history(messages[:-1]))

        deps = deps_override if deps_override is not None else self._deps
        agent = self._get_agent(model)
        full_text = ""
        async with agent.run_stream(
            user_content,
            message_history=history,
            deps=deps,
        ) as result:
            async for chunk in result.stream_text(delta=True):
                full_text += chunk
                yield chunk

            # After stream exhausted, compute and log metrics
            tools_invoked = self._extract_tool_names(result.new_messages())
            user_settings = deps_override.user_settings if deps_override else None
            scoring_tools = [t for t in tools_invoked if t not in ACTION_TOOL_NAMES]
            domain_score = _compute_domain_score(scoring_tools, full_text, user_settings)

            logger.info(
                "chat_metrics conversation_id=%s tools=%s gse_citations=%d domain_score=%d",
                conversation_id,
                tools_invoked,
                len(_GSE_PATTERN.findall(full_text)),
                domain_score,
            )

            if result_sink is not None:
                result_sink["tools"] = tools_invoked
                result_sink["domain_score"] = domain_score

    def get_available_models(self) -> list[str]:
        """Get list of available model names."""
        return list(self._models.keys())
