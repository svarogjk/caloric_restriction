"""
LangChain Service for conversational AI.

Uses LangChain 1.x create_agent (LangGraph-based) with tool-calling support.
Falls back to a plain chain if no tools have been injected.

History management:
- Per-conversation history is maintained externally in PostgreSQL (ConversationService)
- Before passing to the agent, old messages are trimmed via trim_messages()
  once the estimated token count exceeds 4000 tokens (~16,000 chars)
"""

import logging
import os
from pathlib import Path
from typing import AsyncGenerator

from langgraph.prebuilt import create_react_agent
from langchain_core.messages import (
    HumanMessage,
    AIMessage,
    SystemMessage,
    BaseMessage,
    trim_messages,
)
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_mistralai import ChatMistralAI
from langchain_anthropic import ChatAnthropic

logger = logging.getLogger(__name__)

# Path to key files (relative to services directory)
SERVICES_DIR = Path(__file__).parent.parent

# ~4 chars per token; trim to 4000 token budget ≈ 16,000 chars
_MAX_HISTORY_CHARS = 16_000


class LangChainService:
    """Service for LangChain-based conversations with optional tool-calling."""

    def __init__(self) -> None:
        self.models = self._init_models()
        self._system_prompt = self._build_system_prompt()

        # Tools injected after init via set_tools() — invalidates cached agents
        self._tools: list = []
        self._agents: dict = {}  # keyed by model_name

    # ------------------------------------------------------------------
    # Tool injection
    # ------------------------------------------------------------------

    def set_tools(self, tools: list) -> None:
        """
        Inject agent tools.

        Call once at startup after all services are ready.
        Invalidates cached agents so they are rebuilt with the new tools.
        """
        self._tools = tools
        self._agents = {}
        logger.info(f"Agent tools registered: {[t.name for t in tools]}")

    # ------------------------------------------------------------------
    # Model initialisation
    # ------------------------------------------------------------------

    def _init_models(self) -> dict:
        """Initialize LLM models."""
        models = {}

        mistral_key = os.getenv("MISTRAL_KEY")
        if not mistral_key:
            key_file = SERVICES_DIR / "mistral_key.txt"
            if key_file.exists():
                mistral_key = key_file.read_text().strip()
                logger.info("Loaded Mistral key from file")

        if mistral_key:
            models["mistral"] = ChatMistralAI(
                api_key=mistral_key,
                model="mistral-small-latest",
                streaming=True,
                temperature=0.7,
            )
            logger.info("Initialized Mistral model")

        anthropic_key = os.getenv("ANTHROPIC_KEY")
        if not anthropic_key:
            key_file = SERVICES_DIR / "anthropic_key.txt"
            if key_file.exists():
                anthropic_key = key_file.read_text().strip()
                logger.info("Loaded Anthropic key from file")

        if anthropic_key:
            models["anthropic"] = ChatAnthropic(
                api_key=anthropic_key,
                model="claude-3-haiku-20240307",
                streaming=True,
                temperature=0.7,
            )
            logger.info("Initialized Anthropic model")

        if not models:
            logger.warning("No LLM models configured - check API keys")

        return models

    # ------------------------------------------------------------------
    # Agent / chain creation
    # ------------------------------------------------------------------

    def _get_agent(self, model_name: str):
        """Get or create a LangChain 1.x create_agent graph for the given model."""
        if model_name in self._agents:
            return self._agents[model_name]

        if model_name not in self.models:
            raise ValueError(f"Model '{model_name}' not available")

        llm = self.models[model_name]
        agent = create_react_agent(
            llm,
            self._tools,
            prompt=self._system_prompt,
        )
        self._agents[model_name] = agent
        logger.info(
            f"Created agent for model '{model_name}' with {len(self._tools)} tools"
        )
        return agent

    def _create_chain(self, model_name: str):
        """Fallback plain chain (used when no tools are injected)."""
        if model_name not in self.models:
            raise ValueError(f"Model '{model_name}' not available")

        prompt = ChatPromptTemplate.from_messages([
            ("system", self._system_prompt),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{input}"),
        ])
        return prompt | self.models[model_name]

    # ------------------------------------------------------------------
    # History helpers
    # ------------------------------------------------------------------

    def _trim_history(self, messages: list[BaseMessage]) -> list[BaseMessage]:
        """
        Trim history to fit within the context budget.

        Keeps the most recent messages up to _MAX_HISTORY_CHARS characters.
        Uses langchain_core trim_messages with a character-based counter
        (approximation: 4 chars ≈ 1 token, budget = 4000 tokens).
        """
        total_chars = sum(len(getattr(m, "content", "")) for m in messages)
        if total_chars <= _MAX_HISTORY_CHARS:
            return messages

        return trim_messages(
            messages,
            strategy="last",
            max_tokens=_MAX_HISTORY_CHARS,
            token_counter=lambda msgs: sum(
                len(getattr(m, "content", "")) for m in msgs
            ),
            start_on="human",
            end_on=("human", "tool"),
            include_system=False,
        )

    def _convert_messages(self, messages: list[dict]) -> list[BaseMessage]:
        """Convert dict messages to LangChain message objects."""
        type_map = {
            "user": HumanMessage,
            "assistant": AIMessage,
            "system": SystemMessage,
        }
        converted = []
        for msg in messages:
            cls = type_map.get(msg.get("role", "user"))
            if cls:
                converted.append(cls(content=msg.get("content", "")))
        return converted

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
        Generate a complete response.

        Uses tool-calling agent if tools are configured, plain chain otherwise.

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
        augmented_input = user_content
        if estimation_context:
            augmented_input += self._build_context_note(estimation_context)

        history = self._trim_history(self._convert_messages(messages[:-1]))

        if self._tools:
            agent = self._get_agent(model)
            # Build full message list for the agent: history + current input
            agent_messages = history + [HumanMessage(content=augmented_input)]
            result = await agent.ainvoke({"messages": agent_messages})
            # Last message in the result state is the AI response
            output_messages = result.get("messages", [])
            response_text = ""
            for msg in reversed(output_messages):
                if isinstance(msg, AIMessage) and msg.content:
                    content = msg.content
                    if isinstance(content, list):
                        # Anthropic tool-call responses: list of content blocks
                        # Extract only text blocks, skip tool_use blocks
                        parts = [
                            block["text"] if isinstance(block, dict) else str(block)
                            for block in content
                            if not isinstance(block, dict) or block.get("type") == "text"
                        ]
                        response_text = "".join(parts).strip()
                    else:
                        response_text = content
                    if response_text:
                        break
        else:
            chain = self._create_chain(model)
            response = await chain.ainvoke(
                {"history": history, "input": augmented_input}
            )
            response_text = response.content

        tokens_used = None
        return response_text, tokens_used

    async def stream_response(
        self,
        messages: list[dict],
        model: str = "mistral",
        estimation_context: dict | None = None,
        conversation_id: str | None = None,
    ) -> AsyncGenerator[str, None]:
        """
        Stream response tokens.

        When tools are configured, streams via astream_events (agent).
        Falls back to plain chain streaming otherwise.

        Args:
            messages: Full conversation history
            model: Model name
            estimation_context: Optional pre-flight estimation data
            conversation_id: Unused (history is passed directly via messages)

        Yields:
            Response tokens as they are generated
        """
        if not messages:
            yield "Hello! How can I help you with survival analysis today?"
            return

        user_content = messages[-1].get("content", "")
        augmented_input = user_content
        if estimation_context:
            augmented_input += self._build_context_note(estimation_context)

        history = self._trim_history(self._convert_messages(messages[:-1]))

        if self._tools:
            agent = self._get_agent(model)
            agent_messages = history + [HumanMessage(content=augmented_input)]
            async for event in agent.astream_events(
                {"messages": agent_messages}, version="v2"
            ):
                if event["event"] == "on_chat_model_stream":
                    chunk = event["data"].get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        content = chunk.content
                        if isinstance(content, list):
                            for block in content:
                                if isinstance(block, dict) and block.get("type") == "text":
                                    yield block["text"]
                                elif isinstance(block, str):
                                    yield block
                        else:
                            yield content
        else:
            chain = self._create_chain(model)
            async for chunk in chain.astream(
                {"history": history, "input": augmented_input}
            ):
                if hasattr(chunk, "content") and chunk.content:
                    content = chunk.content
                    if isinstance(content, list):
                        for block in content:
                            if isinstance(block, dict) and block.get("type") == "text":
                                yield block["text"]
                            elif isinstance(block, str):
                                yield block
                    else:
                        yield content

    def get_available_models(self) -> list[str]:
        """Get list of available model names."""
        return list(self.models.keys())

    def _build_system_prompt(self) -> str:
        """Build the system prompt for the chat assistant."""
        return """You are a bioinformatics assistant for a GEO Survival Analysis application. You help users analyze gene expression survival associations from NCBI GEO datasets.

You have access to tools that let you directly search datasets, estimate query quality, search GEO in real time, run survival analyses, and look up gene information. Use them proactively.

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
