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
from pathlib import Path
from typing import AsyncGenerator

from pydantic_ai import Agent
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

_SYSTEM_PROMPT = """You are a bioinformatics assistant for a GEO Survival Analysis application. You help users analyze gene expression survival associations from NCBI GEO datasets.

You have access to tools that let you directly search datasets, estimate query quality, search GEO in real time, and look up gene information. Use them proactively.

## Tools Available

- **search_known_datasets**: Search the indexed local GEO dataset catalogue semantically
- **estimate_query**: Check confidence and get suggestions before recommending a run
- **search_geo_datasets**: Live GEO search to preview available datasets
- **get_gene_info**: Retrieve NCBI gene summaries

## Key Concepts
- **Hazard Ratio (HR)**: HR > 1 = worse survival (oncogenic); HR < 1 = protective
- **Kaplan-Meier curves**: Survival probability over time per expression group
- **Log-rank test**: Statistical comparison of survival distributions between groups

## Guidelines
- NEVER run the analysis yourself — the user must click "Run Analysis" explicitly
- Use estimate_query to check confidence and surface the estimation popup for the user
- Use search_known_datasets first to answer "do we have X data?" questions
- Suggest survival-specific query improvements (add "overall survival", "prognosis")
- Explain statistics in accessible terms
- Never provide medical advice or diagnosis"""


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
            system_prompt=_SYSTEM_PROMPT,
            tools=AGENT_TOOLS,
        )
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
    # Public API
    # ------------------------------------------------------------------

    async def generate_response(
        self,
        messages: list[dict],
        model: str = "mistral",
        estimation_context: dict | None = None,
        conversation_id: str | None = None,
    ) -> tuple[str, int | None]:
        """
        Generate a complete (non-streaming) response.

        Args:
            messages: Full conversation history as dicts with 'role'/'content'
            model: Model name ('mistral' or 'anthropic')
            estimation_context: Optional pre-flight estimation data
            conversation_id: Unused (history is passed directly via messages)

        Returns:
            Tuple of (response text, tokens used or None)
        """
        if not messages:
            return "Hello! How can I help you with survival analysis today?", None

        user_content = messages[-1].get("content", "")
        if estimation_context:
            user_content += self._build_context_note(estimation_context)

        history = self._trim_history(self._convert_history(messages[:-1]))

        agent = self._get_agent(model)
        result = await agent.run(
            user_content,
            message_history=history,
            deps=self._deps,
        )
        return result.output, None

    async def stream_response(
        self,
        messages: list[dict],
        model: str = "mistral",
        estimation_context: dict | None = None,
        conversation_id: str | None = None,
    ) -> AsyncGenerator[str, None]:
        """
        Stream response tokens via PydanticAI run_stream.

        Yields text deltas directly — no event filtering needed.

        Args:
            messages: Full conversation history
            model: Model name
            estimation_context: Optional pre-flight estimation data
            conversation_id: Unused (history is passed directly via messages)

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

        agent = self._get_agent(model)
        async with agent.run_stream(
            user_content,
            message_history=history,
            deps=self._deps,
        ) as result:
            async for chunk in result.stream_text(delta=True):
                yield chunk

    def get_available_models(self) -> list[str]:
        """Get list of available model names."""
        return list(self._models.keys())
