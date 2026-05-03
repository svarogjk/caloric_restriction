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

## Response Standards
- Every dataset reference must include its GSE accession (e.g. GSE12345, GSE67890)
- Every hazard ratio claim must name the dataset it came from
- Generic advice without data citations is unacceptable
- NEVER run the analysis yourself — the user clicks "Run Analysis" explicitly

## Key Statistics
- HR > 1: high expression = worse survival (oncogenic marker)
- HR < 1: high expression = protective
- Log-rank p < 0.05 = statistically significant survival difference
- I² > 50% = substantial heterogeneity across datasets"""


def _build_settings_block(user_settings: dict) -> str:
    """Build the dynamic settings section appended to the system prompt per-request."""
    organism = user_settings.get("organism") or "any organism"
    cancer_only = user_settings.get("cancer_genes_only", False)
    n_datasets = user_settings.get("num_datasets", 10)
    genes = user_settings.get("candidate_genes") or []

    lines = ["\n## Active User Configuration (ALREADY SET — do NOT re-suggest these)"]
    lines.append(f"- Organism: {organism}")
    if cancer_only:
        lines.append("- Cancer genes only: True (~600 COSMIC driver genes)")
    else:
        lines.append("- Cancer genes only: False (genome-wide)")
    lines.append(f"- Max datasets to analyze: {n_datasets}")
    if genes:
        genes_str = ", ".join(genes[:10])
        if len(genes) > 10:
            genes_str += f" … ({len(genes)} total)"
        lines.append(f"- Candidate genes: {genes_str}")
    else:
        lines.append("- Candidate genes: none (genome-wide analysis)")
    lines.append(
        f"\nWhen calling search_geo_datasets or get_gene_info, use organism='{organism}' "
        "unless the user explicitly specifies a different organism in their message."
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
            logger.info("Initialized Mistral model")

        anthropic_key = os.getenv("ANTHROPIC_KEY")
        if not anthropic_key:
            key_file = SERVICES_DIR / "anthropic_key.txt"
            if key_file.exists():
                anthropic_key = key_file.read_text().strip()
                logger.info("Loaded Anthropic key from file")

        if anthropic_key:
            models["anthropic"] = AnthropicModel(
                "claude-3-haiku-20240307",
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
            tools=AGENT_TOOLS,
        )

        # Dynamic per-request settings block — reads ctx.deps at run time
        @agent.system_prompt
        async def _settings_prompt(ctx: RunContext[AgentDeps]) -> str:
            if ctx.deps.user_settings:
                return _build_settings_block(ctx.deps.user_settings)
            return ""

        self._agents[model_name] = agent
        logger.info(
            f"Created agent for model '{model_name}' with {len(AGENT_TOOLS)} tools"
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
        model: str = "mistral",
        estimation_context: dict | None = None,
        conversation_id: str | None = None,
        deps_override: AgentDeps | None = None,
    ) -> tuple[str, int | None, int]:
        """
        Generate a complete (non-streaming) response.

        Args:
            messages: Full conversation history as dicts with 'role'/'content'
            model: Model name ('mistral' or 'anthropic')
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
        domain_score = _compute_domain_score(tools_invoked, result.output, user_settings)

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
        model: str = "mistral",
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
            domain_score = _compute_domain_score(tools_invoked, full_text, user_settings)

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
