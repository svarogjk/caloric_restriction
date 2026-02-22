"""
Chat Service - Main orchestrator for chat functionality.

Coordinates conversation management, LangChain responses, query estimation,
and GEO preview functionality.
"""

import logging
from dataclasses import dataclass, field
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.chat.conversation_service import ConversationService, ConversationData
from app.services.chat.estimation_service import QueryEstimationService, EstimationResult
from app.services.chat.langchain_service import LangChainService
from app.services.chat.geo_preview_service import GEOPreviewService

logger = logging.getLogger(__name__)


@dataclass
class ChatResponse:
    """Response from chat service."""

    message_id: str
    content: str
    model_used: str
    estimation: Optional[dict] = None
    suggested_actions: list[str] = field(default_factory=list)


class ChatService:
    """
    Main service orchestrating chat functionality.

    Coordinates:
    - Conversation persistence
    - LangChain response generation
    - Query estimation
    """

    # Keywords that indicate a survival analysis query
    ANALYSIS_KEYWORDS = {
        "survival",
        "prognosis",
        "predict",
        "genes",
        "cancer",
        "lifespan",
        "outcome",
        "hazard",
        "expression",
        "biomarker",
        "analyze",
        "analysis",
        "find genes",
        "search for",
    }

    def __init__(
        self,
        session: AsyncSession,
        langchain_service: Optional[LangChainService] = None,
        estimation_service: Optional[QueryEstimationService] = None,
        geo_preview_service: Optional[GEOPreviewService] = None,
    ):
        self.conversation_service = ConversationService(session)
        self.langchain_service = langchain_service or LangChainService()

        # Create GEO preview service for real-time GEO search previews
        self.geo_preview_service = geo_preview_service or GEOPreviewService()

        # Inject GEO preview service into estimation service
        self.estimation_service = estimation_service or QueryEstimationService(
            geo_preview_service=self.geo_preview_service
        )

    async def create_conversation(
        self,
        title: Optional[str] = None,
        context_type: str = "general",
        user_id: Optional[str] = None,
    ) -> ConversationData:
        """Create a new conversation."""
        conversation = await self.conversation_service.create_conversation(
            title=title,
            context_type=context_type,
            user_id=user_id,
        )
        return self.conversation_service.to_conversation_data(conversation)

    async def get_conversation(
        self,
        conversation_id: str,
    ) -> Optional[ConversationData]:
        """Get a conversation with all messages."""
        conversation = await self.conversation_service.get_conversation(
            conversation_id, include_messages=True
        )
        if conversation:
            return self.conversation_service.to_conversation_data(conversation)
        return None

    async def list_conversations(
        self,
        limit: int = 20,
        offset: int = 0,
        user_id: Optional[str] = None,
    ) -> list[ConversationData]:
        """List all conversations."""
        conversations = await self.conversation_service.list_conversations(
            limit=limit, offset=offset, user_id=user_id
        )
        return [
            ConversationData(
                id=conv.id,
                title=conv.title,
                created_at=conv.created_at,
                updated_at=conv.updated_at,
                context_type=conv.context_type,
                messages=[],  # Don't include messages in list view
            )
            for conv in conversations
        ]

    async def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation."""
        return await self.conversation_service.delete_conversation(conversation_id)

    async def send_message(
        self,
        conversation_id: str,
        content: str,
        model: str = "mistral",
    ) -> ChatResponse:
        """
        Send a user message and get AI response.

        Args:
            conversation_id: The conversation to add the message to
            content: The user's message content
            model: The LLM model to use

        Returns:
            ChatResponse with the assistant's reply
        """
        # 1. Check if this looks like an analysis query and run estimation first
        #    so we can link estimation_id to the user message
        estimation = None
        estimation_dict = None
        saved_estimation_id = None
        if self._looks_like_analysis_query(content):
            estimation = await self.estimation_service.estimate_query(content)
            estimation_dict = {
                "confidence_score": estimation.confidence_score,
                "estimated_datasets": estimation.estimated_datasets,
                "estimated_time_seconds": estimation.estimated_time_seconds,
                "can_proceed": estimation.can_proceed,
                "suggestions": estimation.suggestions,
                "improved_query": estimation.improved_query,
                "geo_preview": estimation.geo_preview,
            }

            saved_est = await self.conversation_service.save_estimation(
                original_query=content,
                confidence_score=estimation.confidence_score,
                estimated_datasets=estimation.estimated_datasets,
                estimated_time_seconds=estimation.estimated_time_seconds,
                can_proceed=estimation.can_proceed,
                suggestions=estimation.suggestions,
                improved_query=estimation.improved_query,
                has_survival_keywords=estimation.validation.get(
                    "has_survival_keywords", False
                ),
                has_cancer_type=estimation.validation.get("has_cancer_type", False),
                has_organism=estimation.validation.get("has_organism", False),
                has_gene_focus=estimation.validation.get("has_gene_focus", False),
            )
            saved_estimation_id = saved_est.id

        # 2. Save user message (with estimation_id if applicable)
        await self.conversation_service.add_message(
            conversation_id=conversation_id,
            role="user",
            content=content,
            estimation_id=saved_estimation_id,
        )

        # 3. Get conversation history
        messages = await self.conversation_service.get_messages_as_dicts(
            conversation_id
        )

        # 4. Generate AI response
        response_content, tokens_used = await self.langchain_service.generate_response(
            messages=messages,
            model=model,
            estimation_context=estimation_dict,
        )

        # 5. Save assistant message
        assistant_message = await self.conversation_service.add_message(
            conversation_id=conversation_id,
            role="assistant",
            content=response_content,
            model_used=model,
            tokens_used=tokens_used,
        )

        # 6. Update conversation title if this is the first exchange
        conversation = await self.conversation_service.get_conversation(
            conversation_id, include_messages=False
        )
        if conversation and conversation.title == "New Conversation":
            # Generate title from first user message
            title = self._generate_title(content)
            await self.conversation_service.update_conversation(
                conversation_id, title=title
            )

        # 7. Extract suggested actions
        suggested_actions = self._extract_actions(response_content, estimation)

        return ChatResponse(
            message_id=assistant_message.id,
            content=response_content,
            model_used=model,
            estimation=estimation_dict,
            suggested_actions=suggested_actions,
        )

    async def stream_message(
        self,
        conversation_id: str,
        content: str,
        model: str = "mistral",
    ) -> AsyncGenerator[str, None]:
        """
        Stream AI response token by token.

        Args:
            conversation_id: The conversation ID
            content: The user's message
            model: The LLM model to use

        Yields:
            Response tokens as they are generated
        """
        # Run estimation first (if applicable) so estimation_id can be linked to user msg
        estimation_context = None
        saved_estimation_id = None
        if self._looks_like_analysis_query(content):
            estimation = await self.estimation_service.estimate_query(content)
            estimation_context = {
                "confidence_score": estimation.confidence_score,
                "estimated_datasets": estimation.estimated_datasets,
                "estimated_time_seconds": estimation.estimated_time_seconds,
                "can_proceed": estimation.can_proceed,
                "suggestions": estimation.suggestions,
                "geo_preview": estimation.geo_preview,
            }

            saved_est = await self.conversation_service.save_estimation(
                original_query=content,
                confidence_score=estimation.confidence_score,
                estimated_datasets=estimation.estimated_datasets,
                estimated_time_seconds=estimation.estimated_time_seconds,
                can_proceed=estimation.can_proceed,
                suggestions=estimation.suggestions,
                improved_query=estimation.improved_query,
                has_survival_keywords=estimation.validation.get(
                    "has_survival_keywords", False
                ),
                has_cancer_type=estimation.validation.get("has_cancer_type", False),
                has_organism=estimation.validation.get("has_organism", False),
                has_gene_focus=estimation.validation.get("has_gene_focus", False),
            )
            saved_estimation_id = saved_est.id

            # Yield estimation summary as first chunk
            yield self._format_estimation_summary(estimation)

        # Save user message (with estimation_id if applicable)
        await self.conversation_service.add_message(
            conversation_id=conversation_id,
            role="user",
            content=content,
            estimation_id=saved_estimation_id,
        )

        # Get history
        messages = await self.conversation_service.get_messages_as_dicts(
            conversation_id
        )

        # Stream response
        full_response = ""
        async for chunk in self.langchain_service.stream_response(
            messages, model, estimation_context=estimation_context
        ):
            full_response += chunk
            yield chunk

        # Save complete response (tokens not available from streaming)
        await self.conversation_service.add_message(
            conversation_id=conversation_id,
            role="assistant",
            content=full_response,
            model_used=model,
        )

    def _format_estimation_summary(self, estimation: EstimationResult) -> str:
        """Format estimation result as a user-friendly summary."""
        lines = []
        lines.append("\n**Query Analysis Summary**\n")

        confidence_pct = int(estimation.confidence_score * 100)
        lines.append(f"Confidence: {confidence_pct}%\n")

        if estimation.geo_preview:
            preview = estimation.geo_preview
            total = preview.get("total_datasets", 0)
            survival = preview.get("datasets_with_survival_keywords", 0)
            lines.append(f"Found {total} matching datasets in GEO")
            if survival > 0:
                lines.append(f"  - {survival} mention survival/outcome data")

            # Platform breakdown
            platform_counts = preview.get("platform_counts", {})
            if platform_counts:
                top_platforms = sorted(
                    platform_counts.items(), key=lambda x: x[1], reverse=True
                )[:3]
                platforms_str = ", ".join(
                    f"{p}: {c}" for p, c in top_platforms
                )
                lines.append(f"  - Platforms: {platforms_str}")

            # Warnings
            warnings = preview.get("warnings", [])
            for warning in warnings[:2]:
                lines.append(f"  - {warning}")

        if estimation.suggestions:
            lines.append("\nSuggestions:")
            for suggestion in estimation.suggestions[:3]:
                lines.append(f"  - {suggestion}")

        lines.append("\n---\n")
        return "\n".join(lines)

    async def estimate_query(self, query: str) -> EstimationResult:
        """
        Estimate success likelihood for a query.

        Can be called independently before sending a message.
        """
        return await self.estimation_service.estimate_query(query)

    def _looks_like_analysis_query(self, message: str) -> bool:
        """Detect if message is asking for survival analysis."""
        message_lower = message.lower()
        return any(kw in message_lower for kw in self.ANALYSIS_KEYWORDS)

    def _generate_title(self, first_message: str) -> str:
        """Generate a conversation title from the first message."""
        # Take first 50 chars, cut at word boundary
        title = first_message[:50]
        if len(first_message) > 50:
            # Cut at last space
            last_space = title.rfind(" ")
            if last_space > 20:
                title = title[:last_space]
            title += "..."
        return title

    def _extract_actions(
        self,
        content: str,
        estimation: Optional[EstimationResult],
    ) -> list[str]:
        """Extract suggested actions from response and estimation."""
        actions = []

        content_lower = content.lower()

        # Check for action-like phrases in response
        if "run the analysis" in content_lower or "perform the analysis" in content_lower:
            actions.append("run_analysis")

        if "modify" in content_lower or "try" in content_lower:
            actions.append("modify_query")

        # Add actions based on estimation
        if estimation:
            if estimation.can_proceed:
                if "run_analysis" not in actions:
                    actions.append("run_analysis")
            if estimation.improved_query:
                actions.append("use_improved_query")

        return actions
