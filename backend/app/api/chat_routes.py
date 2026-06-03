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
from app.api.dependencies import get_current_active_user, get_optional_current_user
from app.services.chat import ChatService, PydanticAIService, QueryEstimationService
from app.services.chat.agent_tools import AgentDeps

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

# Shared service instances
_pydantic_ai_service: Optional[PydanticAIService] = None
_estimation_service: Optional[QueryEstimationService] = None


def get_pydantic_ai_service() -> PydanticAIService:
    """Get or create PydanticAI service singleton."""
    global _pydantic_ai_service
    if _pydantic_ai_service is None:
        _pydantic_ai_service = PydanticAIService()
    return _pydantic_ai_service


def get_estimation_service() -> QueryEstimationService:
    """Get or create estimation service singleton."""
    global _estimation_service
    if _estimation_service is None:
        _estimation_service = QueryEstimationService()
    return _estimation_service


def set_deps(deps: AgentDeps) -> None:
    """
    Inject service dependencies into the PydanticAI service singleton.

    Called from app lifespan once all services are ready.
    """
    get_pydantic_ai_service().set_deps(deps)
    logger.info("AgentDeps injected into PydanticAIService")


async def get_chat_service(
    db: AsyncSession = Depends(get_db),
) -> ChatService:
    """Dependency to get ChatService instance."""
    return ChatService(
        session=db,
        langchain_service=get_pydantic_ai_service(),
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


class UserSettings(BaseModel):
    """User's active analysis configuration, forwarded from the frontend UI."""

    organism: Optional[str] = None
    cancer_genes_only: bool = False
    num_datasets: int = 10
    ranking_multiplier: float = 3.0
    candidate_genes: Optional[list[str]] = None


class SendMessageRequest(BaseModel):
    """Request to send a message."""

    content: str = Field(..., min_length=1, max_length=5000)
    model: str = Field(default="mistral", pattern="^(mistral|anthropic|claude)$")
    stream: bool = False
    user_settings: Optional[UserSettings] = None


class MessageResponse(BaseModel):
    """Response for a single message."""

    message_id: str
    role: str
    content: str
    created_at: str
    model_used: Optional[str] = None
    estimation: Optional[dict] = None
    suggested_actions: list[str] = []
    domain_score: Optional[int] = None


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
    current_user=Depends(get_optional_current_user),
):
    """
    Create a new conversation. Works for both authenticated and anonymous users.
    Anonymous conversations are ephemeral and not tied to a user account.
    """
    conversation = await chat_service.create_conversation(
        title=request.title,
        context_type=request.context_type,
        user_id=current_user.id if current_user else None,
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
    current_user=Depends(get_optional_current_user),
):
    """
    List conversations for the authenticated user. Returns empty list for anonymous users.
    """
    if not current_user:
        return []
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
    current_user=Depends(get_optional_current_user),
):
    """
    Send a message and get AI response.

    Args:
        conversation_id: The conversation ID
        request: SendMessageRequest with content, model, and optional user_settings

    Returns:
        MessageResponse with the AI's reply and domain_score
    """
    # Check if conversation exists
    conversation = await chat_service.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Map "claude" to "anthropic" for internal use
    model = request.model
    if model == "claude":
        model = "anthropic"

    user_settings_dict = request.user_settings.model_dump() if request.user_settings else None
    user_id = current_user.id if current_user else None

    if request.stream:
        # Return streaming response
        async def generate():
            full_content = ""
            stream_sink: dict = {}
            async for chunk in chat_service.stream_message(
                conversation_id=conversation_id,
                content=request.content,
                model=model,
                user_settings=user_settings_dict,
                user_id=user_id,
                result_sink=stream_sink,
            ):
                full_content += chunk
                yield f"data: {json.dumps({'type': 'token', 'content': chunk})}\n\n"

            estimation_for_actions = stream_sink.get("estimation")
            suggested_actions = chat_service._extract_actions(full_content, estimation=estimation_for_actions)
            domain_score = stream_sink.get("domain_score", 0)

            yield f"data: {json.dumps({'type': 'message_complete', 'message': {'message_id': str(uuid.uuid4()), 'role': 'assistant', 'content': full_content, 'created_at': datetime.utcnow().isoformat(), 'model_used': model, 'suggested_actions': suggested_actions, 'domain_score': domain_score}})}\n\n"
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
        user_settings=user_settings_dict,
        user_id=user_id,
    )

    return MessageResponse(
        message_id=response.message_id,
        role="assistant",
        content=response.content,
        created_at=datetime.utcnow().isoformat(),
        model_used=response.model_used,
        estimation=response.estimation,
        suggested_actions=response.suggested_actions,
        domain_score=response.domain_score,
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
    return get_pydantic_ai_service().get_available_models()


# ==================== F21: Clinician interpretation summary ====================

class InterpretRequest(BaseModel):
    """Request a plain-language clinician summary grounded in a real analysis."""
    query: str
    model: str = "mistral"
    # Compact, pre-extracted genes so the summary is grounded and cannot drift:
    # [{gene_symbol, avg_hazard_ratio, avg_cox_p_value, n_datasets, predominant_risk, datasets:[GSE...]}]
    genes: list[dict] = Field(default_factory=list)
    n_datasets_with_survival: int = 0


class InterpretResponse(BaseModel):
    summary: str
    domain_score: int


def _build_interpretation_prompt(req: InterpretRequest) -> str:
    """Ground the LLM in the actual result so it cites real genes/HRs/GSEs."""
    lines: list[str] = []
    for g in req.genes[:8]:
        symbol = g.get("gene_symbol") or g.get("gene_id") or "?"
        hr = g.get("avg_hazard_ratio")
        p = g.get("avg_cox_p_value")
        nd = g.get("n_datasets")
        risk = g.get("predominant_risk", "")
        gses = ", ".join((g.get("datasets") or [])[:4])
        hr_s = f"{hr:.2f}" if isinstance(hr, (int, float)) else "NA"
        p_s = f"{p:.2e}" if isinstance(p, (int, float)) else "NA"
        lines.append(
            f"- {symbol}: HR={hr_s}, p={p_s}, significant in {nd} cohorts "
            f"({risk}); datasets: {gses}"
        )
    genes_block = "\n".join(lines) if lines else "(no genes provided)"

    return (
        f"A user ran a cross-cohort GEO survival analysis for: \"{req.query}\". "
        f"It found prognostic genes across {req.n_datasets_with_survival} independent cohorts "
        f"with survival data. Top genes:\n{genes_block}\n\n"
        "Write a concise plain-language interpretation for an oncologist audience. Requirements:\n"
        "1. Reference the specific genes, their hazard ratios, and GSE accession IDs above.\n"
        "2. Explain what HR>1 vs HR<1 means for risk in lay terms.\n"
        "3. Emphasise this is PROGNOSTIC (outcome association), NOT predictive of any drug response, "
        "and is research-use-only — never a treatment recommendation.\n"
        "4. Keep it under 180 words. Do not invent genes, datasets, or numbers not listed above."
    )


@router.post("/interpret", response_model=InterpretResponse)
async def interpret_results(request: InterpretRequest):
    """F21 — generate an AI clinician summary grounded in a real AnalysisResponse.

    Reuses the pydantic-ai agent (so the chat differentiation/tooling rules apply)
    and returns the honest Domain Score for the generated text.
    """
    model = "anthropic" if request.model == "claude" else request.model
    service = get_pydantic_ai_service()
    prompt = _build_interpretation_prompt(request)
    try:
        summary, _tokens, domain_score = await service.generate_response(
            messages=[{"role": "user", "content": prompt}],
            model=model,
            conversation_id="interpret",
        )
    except (RuntimeError, ValueError, ConnectionError) as e:
        logger.warning("Interpretation failed: %s", e)
        raise HTTPException(status_code=502, detail="Interpretation service temporarily unavailable")

    return InterpretResponse(summary=summary, domain_score=domain_score)
