"""
API routes for AI Chat functionality.

Provides endpoints for conversation management, messaging, and query estimation.
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_db
from app.models.database import User
from app.api.dependencies import get_current_active_user
from app.services.chat import ChatService, LangChainService, QueryEstimationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

# Shared service instances
_langchain_service: Optional[LangChainService] = None
_estimation_service: Optional[QueryEstimationService] = None


def get_langchain_service() -> LangChainService:
    """Get or create LangChain service singleton."""
    global _langchain_service
    if _langchain_service is None:
        _langchain_service = LangChainService()
    return _langchain_service


def get_estimation_service() -> QueryEstimationService:
    """Get or create estimation service singleton."""
    global _estimation_service
    if _estimation_service is None:
        _estimation_service = QueryEstimationService()
    return _estimation_service


def set_tools(tools: list) -> None:
    """
    Inject agent tools into the LangChain service singleton.

    Called from app lifespan once all services are ready.
    """
    get_langchain_service().set_tools(tools)
    logger.info(f"Injected {len(tools)} tools into LangChainService")


async def get_chat_service(
    db: AsyncSession = Depends(get_db),
) -> ChatService:
    """Dependency to get ChatService instance."""
    return ChatService(
        session=db,
        langchain_service=get_langchain_service(),
        estimation_service=get_estimation_service(),
    )


# ==================== Request/Response Models ====================


class CreateConversationRequest(BaseModel):
    """Request to create a new conversation."""

    title: Optional[str] = None
    context_type: str = Field(
        default="general", pattern="^(general|analysis|interpretation)$"
    )


class CreateConversationResponse(BaseModel):
    """Response after creating a conversation."""

    conversation_id: str
    title: str
    created_at: str


class SendMessageRequest(BaseModel):
    """Request to send a message."""

    content: str = Field(..., min_length=1, max_length=5000)
    model: str = Field(default="mistral", pattern="^(mistral|anthropic|claude)$")
    stream: bool = False


class MessageResponse(BaseModel):
    """Response for a single message."""

    message_id: str
    role: str
    content: str
    created_at: str
    model_used: Optional[str] = None
    estimation: Optional[dict] = None
    suggested_actions: list[str] = []


class ConversationResponse(BaseModel):
    """Response for a conversation with messages."""

    id: str
    title: Optional[str]
    created_at: str
    updated_at: str
    context_type: str
    messages: list[MessageResponse]


class ConversationListItem(BaseModel):
    """Summary item for conversation list."""

    id: str
    title: Optional[str]
    created_at: str
    updated_at: str
    context_type: str


class EstimateQueryRequest(BaseModel):
    """Request to estimate query success."""

    query: str = Field(..., min_length=5, max_length=500)


class EstimateQueryResponse(BaseModel):
    """Response for query estimation."""

    confidence_score: float
    estimated_datasets: int
    estimated_time_seconds: float
    can_proceed: bool
    suggestions: list[str]
    improved_query: Optional[str]
    validation: dict


# ==================== Endpoints ====================


@router.post("/conversations", response_model=CreateConversationResponse)
async def create_conversation(
    request: CreateConversationRequest,
    chat_service: ChatService = Depends(get_chat_service),
    current_user: User = Depends(get_current_active_user),
):
    """
    Create a new conversation.

    Args:
        request: CreateConversationRequest with optional title and context

    Returns:
        CreateConversationResponse with the new conversation ID
    """
    conversation = await chat_service.create_conversation(
        title=request.title,
        context_type=request.context_type,
        user_id=current_user.id,
    )

    return CreateConversationResponse(
        conversation_id=conversation.id,
        title=conversation.title or "New Conversation",
        created_at=conversation.created_at.isoformat(),
    )


@router.get("/conversations", response_model=list[ConversationListItem])
async def list_conversations(
    limit: int = 20,
    offset: int = 0,
    chat_service: ChatService = Depends(get_chat_service),
    current_user: User = Depends(get_current_active_user),
):
    """
    List conversations for the authenticated user, ordered by most recent.

    Args:
        limit: Maximum number of conversations to return
        offset: Number of conversations to skip

    Returns:
        List of conversation summaries
    """
    conversations = await chat_service.list_conversations(
        limit=limit, offset=offset, user_id=current_user.id
    )

    return [
        ConversationListItem(
            id=conv.id,
            title=conv.title,
            created_at=conv.created_at.isoformat(),
            updated_at=conv.updated_at.isoformat(),
            context_type=conv.context_type,
        )
        for conv in conversations
    ]


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    chat_service: ChatService = Depends(get_chat_service),
):
    """
    Get a conversation with all its messages.

    Args:
        conversation_id: The conversation ID

    Returns:
        ConversationResponse with all messages
    """
    conversation = await chat_service.get_conversation(conversation_id)

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return ConversationResponse(
        id=conversation.id,
        title=conversation.title,
        created_at=conversation.created_at.isoformat(),
        updated_at=conversation.updated_at.isoformat(),
        context_type=conversation.context_type,
        messages=[
            MessageResponse(
                message_id=msg.id,
                role=msg.role,
                content=msg.content,
                created_at=msg.created_at.isoformat(),
                model_used=msg.model_used,
            )
            for msg in conversation.messages
        ],
    )


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    chat_service: ChatService = Depends(get_chat_service),
):
    """
    Delete a conversation (soft delete).

    Args:
        conversation_id: The conversation ID to delete

    Returns:
        Status confirmation
    """
    success = await chat_service.delete_conversation(conversation_id)

    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return {"status": "deleted", "conversation_id": conversation_id}


@router.post(
    "/conversations/{conversation_id}/messages", response_model=MessageResponse
)
async def send_message(
    conversation_id: str,
    request: SendMessageRequest,
    chat_service: ChatService = Depends(get_chat_service),
):
    """
    Send a message and get AI response.

    Args:
        conversation_id: The conversation ID
        request: SendMessageRequest with content and model

    Returns:
        MessageResponse with the AI's reply
    """
    # Check if conversation exists
    conversation = await chat_service.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Map "claude" to "anthropic" for internal use
    model = request.model
    if model == "claude":
        model = "anthropic"

    if request.stream:
        # Return streaming response
        async def generate():
            full_content = ""
            async for chunk in chat_service.stream_message(
                conversation_id=conversation_id,
                content=request.content,
                model=model,
            ):
                full_content += chunk
                yield f"data: {json.dumps({'type': 'token', 'content': chunk})}\n\n"

            # Send message_complete so the frontend Promise resolves
            yield f"data: {json.dumps({'type': 'message_complete', 'message': {'message_id': str(uuid.uuid4()), 'role': 'assistant', 'content': full_content, 'created_at': datetime.utcnow().isoformat(), 'model_used': model, 'suggested_actions': []}})}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
        )

    # Non-streaming response
    response = await chat_service.send_message(
        conversation_id=conversation_id,
        content=request.content,
        model=model,
    )

    return MessageResponse(
        message_id=response.message_id,
        role="assistant",
        content=response.content,
        created_at=datetime.utcnow().isoformat(),
        model_used=response.model_used,
        estimation=response.estimation,
        suggested_actions=response.suggested_actions,
    )


@router.post("/estimate", response_model=EstimateQueryResponse)
async def estimate_query(
    request: EstimateQueryRequest,
    chat_service: ChatService = Depends(get_chat_service),
):
    """
    Estimate success likelihood for a survival analysis query.

    This endpoint can be called before sending a message to get
    feedback on query quality and improvement suggestions.

    Args:
        request: EstimateQueryRequest with the query to evaluate

    Returns:
        EstimateQueryResponse with confidence score and suggestions
    """
    estimation = await chat_service.estimate_query(request.query)

    return EstimateQueryResponse(
        confidence_score=estimation.confidence_score,
        estimated_datasets=estimation.estimated_datasets,
        estimated_time_seconds=estimation.estimated_time_seconds,
        can_proceed=estimation.can_proceed,
        suggestions=estimation.suggestions,
        improved_query=estimation.improved_query,
        validation=estimation.validation,
    )


@router.get("/models")
async def get_chat_models():
    """
    Get available LLM models for chat.

    Returns:
        List of available model names
    """
    langchain = get_langchain_service()
    return langchain.get_available_models()
