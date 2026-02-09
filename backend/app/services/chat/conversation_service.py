"""
Conversation service for CRUD operations on conversations and messages.
"""

import logging
from datetime import datetime
from typing import Optional
from dataclasses import dataclass

from sqlalchemy import select, update, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.database import Conversation, Message, QueryEstimation

logger = logging.getLogger(__name__)


@dataclass
class MessageData:
    """Data class for message information."""

    id: str
    role: str
    content: str
    created_at: datetime
    model_used: Optional[str] = None
    tokens_used: Optional[int] = None


@dataclass
class ConversationData:
    """Data class for conversation information."""

    id: str
    title: Optional[str]
    created_at: datetime
    updated_at: datetime
    context_type: str
    messages: list[MessageData]


class ConversationService:
    """Service for managing conversations and messages."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_conversation(
        self,
        title: Optional[str] = None,
        context_type: str = "general",
    ) -> Conversation:
        """Create a new conversation."""
        conversation = Conversation(
            title=title or "New Conversation",
            context_type=context_type,
        )
        self.session.add(conversation)
        await self.session.flush()
        # Refresh to load the messages relationship (empty for new conversations)
        # This prevents lazy loading issues in async context
        await self.session.refresh(conversation, ["messages"])
        logger.info(f"Created conversation: {conversation.id}")
        return conversation

    async def get_conversation(
        self,
        conversation_id: str,
        include_messages: bool = True,
    ) -> Optional[Conversation]:
        """Get a conversation by ID."""
        query = select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.deleted_at.is_(None),
        )

        if include_messages:
            query = query.options(selectinload(Conversation.messages))

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list_conversations(
        self,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Conversation]:
        """List conversations ordered by most recent update."""
        query = (
            select(Conversation)
            .where(Conversation.deleted_at.is_(None))
            .order_by(desc(Conversation.updated_at))
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update_conversation(
        self,
        conversation_id: str,
        title: Optional[str] = None,
        context_type: Optional[str] = None,
        analysis_query: Optional[str] = None,
    ) -> Optional[Conversation]:
        """Update a conversation's metadata."""
        update_data = {"updated_at": datetime.utcnow()}

        if title is not None:
            update_data["title"] = title
        if context_type is not None:
            update_data["context_type"] = context_type
        if analysis_query is not None:
            update_data["analysis_query"] = analysis_query

        await self.session.execute(
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(**update_data)
        )
        await self.session.flush()

        return await self.get_conversation(conversation_id, include_messages=False)

    async def delete_conversation(self, conversation_id: str) -> bool:
        """Soft delete a conversation."""
        await self.session.execute(
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(deleted_at=datetime.utcnow())
        )
        await self.session.flush()
        logger.info(f"Deleted conversation: {conversation_id}")
        return True

    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        model_used: Optional[str] = None,
        tokens_used: Optional[int] = None,
        estimation_id: Optional[str] = None,
    ) -> Message:
        """Add a message to a conversation."""
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            model_used=model_used,
            tokens_used=tokens_used,
            estimation_id=estimation_id,
        )
        self.session.add(message)

        # Update conversation's updated_at
        await self.session.execute(
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(updated_at=datetime.utcnow())
        )

        await self.session.flush()
        logger.debug(f"Added {role} message to conversation {conversation_id}")
        return message

    async def get_messages(
        self,
        conversation_id: str,
        limit: Optional[int] = None,
    ) -> list[Message]:
        """Get messages for a conversation."""
        query = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
        )

        if limit:
            query = query.limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_messages_as_dicts(
        self,
        conversation_id: str,
        limit: Optional[int] = None,
    ) -> list[dict]:
        """Get messages as dictionaries for LangChain."""
        messages = await self.get_messages(conversation_id, limit)
        return [
            {
                "role": msg.role,
                "content": msg.content,
                "created_at": msg.created_at.isoformat(),
            }
            for msg in messages
        ]

    async def save_estimation(
        self,
        original_query: str,
        confidence_score: float,
        estimated_datasets: Optional[int] = None,
        estimated_time_seconds: Optional[float] = None,
        can_proceed: bool = True,
        improved_query: Optional[str] = None,
        suggestions: Optional[list[str]] = None,
        has_survival_keywords: bool = False,
        has_cancer_type: bool = False,
        has_organism: bool = False,
        has_gene_focus: bool = False,
    ) -> QueryEstimation:
        """Save a query estimation result."""
        estimation = QueryEstimation(
            original_query=original_query,
            confidence_score=confidence_score,
            estimated_datasets=estimated_datasets,
            estimated_time_seconds=estimated_time_seconds,
            can_proceed=can_proceed,
            improved_query=improved_query,
            suggestions=suggestions,
            has_survival_keywords=has_survival_keywords,
            has_cancer_type=has_cancer_type,
            has_organism=has_organism,
            has_gene_focus=has_gene_focus,
        )
        self.session.add(estimation)
        await self.session.flush()
        return estimation

    def to_conversation_data(self, conversation: Conversation) -> ConversationData:
        """Convert a Conversation model to ConversationData."""
        messages = [
            MessageData(
                id=msg.id,
                role=msg.role,
                content=msg.content,
                created_at=msg.created_at,
                model_used=msg.model_used,
                tokens_used=msg.tokens_used,
            )
            for msg in conversation.messages
        ]

        return ConversationData(
            id=conversation.id,
            title=conversation.title,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            context_type=conversation.context_type,
            messages=messages,
        )
