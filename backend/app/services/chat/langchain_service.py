"""
LangChain Service for conversational AI.

Provides conversation chain management and streaming support.
"""

import os
import logging
from typing import AsyncGenerator

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_mistralai import ChatMistralAI
from langchain_anthropic import ChatAnthropic

logger = logging.getLogger(__name__)


class LangChainService:
    """Service for LangChain-based conversations."""

    def __init__(self):
        self.models = self._init_models()
        self._system_prompt = self._build_system_prompt()

    def _init_models(self) -> dict:
        """Initialize LLM models."""
        models = {}

        # Mistral
        mistral_key = os.getenv("MISTRAL_KEY")
        if mistral_key:
            models["mistral"] = ChatMistralAI(
                api_key=mistral_key,
                model="mistral-small-latest",
                streaming=True,
                temperature=0.7,
            )
            logger.info("Initialized Mistral model")

        # Anthropic
        anthropic_key = os.getenv("ANTHROPIC_KEY")
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

    def _build_system_prompt(self) -> str:
        """Build the system prompt for the chat assistant."""
        return """You are a bioinformatics assistant specialized in survival analysis of gene expression data from NCBI GEO datasets.

## Your Expertise
- Survival analysis methods (Kaplan-Meier, Cox regression)
- Gene expression data analysis
- NCBI GEO database navigation
- Statistical interpretation of results

## Key Concepts
- **Hazard Ratio (HR)**: Ratio of hazard rates between groups
  - HR > 1: Increased risk (worse survival)
  - HR < 1: Decreased risk (better survival / protective)
- **Kaplan-Meier curves**: Show survival probability over time
- **Log-rank test**: Compares survival distributions

## Your Capabilities
1. Help users formulate effective survival analysis queries
2. Explain statistical results and their clinical implications
3. Suggest improvements to queries for better results
4. Interpret hazard ratios, p-values, and confidence intervals
5. Recommend relevant genes or datasets to explore

## Guidelines
- Be concise but informative
- Use scientific terminology appropriately
- Provide actionable suggestions
- When uncertain about data availability, be honest about limitations
- Never provide medical advice or diagnosis

## Response Style
- Start with a direct answer to the user's question
- Provide relevant context and explanations
- End with a suggestion or next step when appropriate"""

    def _create_chain(self, model_name: str):
        """Create a conversation chain for the specified model."""
        if model_name not in self.models:
            raise ValueError(f"Model '{model_name}' not available")

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", self._system_prompt),
                MessagesPlaceholder(variable_name="history"),
                ("human", "{input}"),
            ]
        )

        return prompt | self.models[model_name]

    def _convert_messages(self, messages: list[dict]) -> list[BaseMessage]:
        """Convert dict messages to LangChain message objects."""
        converted = []
        for msg in messages:
            content = msg.get("content", "")
            role = msg.get("role", "user")

            if role == "user":
                converted.append(HumanMessage(content=content))
            elif role == "assistant":
                converted.append(AIMessage(content=content))
            elif role == "system":
                converted.append(SystemMessage(content=content))

        return converted

    async def generate_response(
        self,
        messages: list[dict],
        model: str = "mistral",
        estimation_context: dict | None = None,
    ) -> str:
        """
        Generate a complete response.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model to use ('mistral' or 'anthropic')
            estimation_context: Optional query estimation data

        Returns:
            The assistant's response text
        """
        if not messages:
            return "Hello! How can I help you with survival analysis today?"

        chain = self._create_chain(model)

        # Split history and current input
        history = self._convert_messages(messages[:-1])
        current_input = messages[-1].get("content", "")

        # Add estimation context if available
        if estimation_context:
            confidence = estimation_context.get("confidence_score", 0)
            suggestions = estimation_context.get("suggestions", [])
            geo_preview = estimation_context.get("geo_preview")

            context_note = f"\n\n[Query Analysis: {confidence:.0%} confidence"

            # Add GEO preview info if available
            if geo_preview:
                total = geo_preview.get("total_datasets", 0)
                survival_count = geo_preview.get("datasets_with_survival_keywords", 0)
                context_note += f", Found {total} datasets ({survival_count} with survival data)"

                # Add platform info
                platform_counts = geo_preview.get("platform_counts", {})
                if platform_counts:
                    platform_diversity = geo_preview.get("platform_diversity", "unknown")
                    context_note += f", Platform diversity: {platform_diversity}"

                # Add warnings
                warnings = geo_preview.get("warnings", [])
                if warnings:
                    context_note += f", Warnings: {warnings[0][:50]}..."

            if suggestions:
                context_note += f", Suggestions: {'; '.join(suggestions[:2])}"
            context_note += "]"
            current_input += context_note

        response = await chain.ainvoke({"history": history, "input": current_input})

        return response.content

    async def stream_response(
        self,
        messages: list[dict],
        model: str = "mistral",
        estimation_context: dict | None = None,
    ) -> AsyncGenerator[str, None]:
        """
        Stream response tokens.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model to use
            estimation_context: Optional query estimation data

        Yields:
            Response tokens as they are generated
        """
        if not messages:
            yield "Hello! How can I help you with survival analysis today?"
            return

        chain = self._create_chain(model)

        history = self._convert_messages(messages[:-1])
        current_input = messages[-1].get("content", "")

        # Add estimation context if available (same as generate_response)
        if estimation_context:
            confidence = estimation_context.get("confidence_score", 0)
            suggestions = estimation_context.get("suggestions", [])
            geo_preview = estimation_context.get("geo_preview")

            context_note = f"\n\n[Query Analysis: {confidence:.0%} confidence"

            # Add GEO preview info
            if geo_preview:
                total = geo_preview.get("total_datasets", 0)
                survival_count = geo_preview.get("datasets_with_survival_keywords", 0)
                context_note += f", Found {total} datasets ({survival_count} with survival data)"

            if suggestions:
                context_note += f", Suggestions: {'; '.join(suggestions[:2])}"
            context_note += "]"
            current_input += context_note

        async for chunk in chain.astream({"history": history, "input": current_input}):
            if hasattr(chunk, "content") and chunk.content:
                yield chunk.content

    def get_available_models(self) -> list[str]:
        """Get list of available model names."""
        return list(self.models.keys())
