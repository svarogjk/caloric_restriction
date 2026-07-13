"""
API routes for AI Chat functionality.

Provides endpoints for conversation management, messaging, and query estimation.
"""

import json
import logging
import re
import uuid
from collections import OrderedDict
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_db
from app.models.database import User
from app.models.signature_models import ARM_COMPARISON_CAVEAT, TreatmentKMEvidence
from app.api.dependencies import get_current_active_user, get_optional_current_user
from app.services.chat import ChatService, PydanticAIService, QueryEstimationService
from app.services.chat.agent_tools import AgentDeps
from app.services.drug_synonym_service import get_drug_synonym_service
from app.services.treatment_context_service import get_treatment_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

# Shared service instances
_pydantic_ai_service: Optional[PydanticAIService] = None
_estimation_service: Optional[QueryEstimationService] = None
# Injected at startup for the grounded therapy-rationale endpoint.
_signature_service = None
_therapy_evidence_service = None


def set_therapy_services(signature_service, therapy_evidence_service) -> None:
    """Inject the signature store + therapy evidence index (called at startup)."""
    global _signature_service, _therapy_evidence_service
    _signature_service = signature_service
    _therapy_evidence_service = therapy_evidence_service


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
        f"It surfaced expression biomarkers across {req.n_datasets_with_survival} independent cohorts "
        f"with survival data; some are predictive (their survival effect differs by treatment arm). "
        f"Top genes:\n{genes_block}\n\n"
        "Write a concise plain-language interpretation for an oncologist audience. Requirements:\n"
        "1. Reference the specific genes, their hazard ratios, and GSE accession IDs above.\n"
        "2. Explain what HR>1 vs HR<1 means for risk in lay terms, and note that a 'predictive' "
        "biomarker is one whose effect depends on treatment.\n"
        "3. Frame any treatment angle as ADVISORY and hypothesis-generating — suggestions to discuss "
        "with the tumour board, grounded in the data, to be validated prospectively. Research use only; "
        "not a binding clinical decision or a prescription.\n"
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


# ============ Grounded therapeutic-rationale (Oncologist Mode) ============

class TherapyRationaleRequest(BaseModel):
    """Request AI 'treatments to consider/discuss' for a patient's risk-driving
    genes — advisory suggestions grounded in documented CIViC/DGIdb evidence."""
    model_id: str
    genes: list[str] = Field(default_factory=list, description="Risk-driving genes; if empty, derived from the model")
    risk_group: Optional[str] = None
    model: str = "mistral"


class TherapyEvidenceRecord(BaseModel):
    gene: str
    source: str                              # "CIViC" | "DGIdb"
    drug: str
    evidence_type: Optional[str] = None      # CIViC
    significance: Optional[str] = None
    direction: Optional[str] = None
    evidence_level: Optional[str] = None
    disease: Optional[str] = None
    url: Optional[str] = None
    interaction_type: Optional[str] = None   # DGIdb
    approved: Optional[bool] = None
    source_db: Optional[str] = None
    # Real-GEO-cohort survival evidence for this drug (F24b), attached for
    # the top few highest-confidence rows only; see _select_top_drugs.
    cohort_km: Optional[TreatmentKMEvidence] = None


class TherapyRationaleResponse(BaseModel):
    rationale: str
    evidence: list[TherapyEvidenceRecord]
    domain_score: int
    disclaimer: str = (
        "Advisory only — treatments to consider and discuss with the care team, "
        "grounded in documented biomarker–therapy evidence from public knowledge "
        "bases and historical GEO cohort outcomes. Hypothesis-generating and "
        "research use only; not a prescription, and not a guarantee that this "
        "patient will respond. Validate prospectively."
    )


# Imperative / prescribing phrasing we refuse to emit. Treatment guidance is
# advisory ("to consider/discuss"), never directive — this keeps us a research
# information source, on the non-device side of the line.
_PRESCRIBING_PATTERN = re.compile(
    r"\b(administer|prescribe|prescribing|initiate (?:therapy|treatment)|"
    r"start (?:the )?(?:patient|therapy|treatment)|"
    r"should (?:receive|be (?:treated|given|started)|take|be put on)|"
    r"we recommend (?:treating|treatment|starting)|the patient (?:should|must))\b",
    re.IGNORECASE,
)


def _build_therapy_prompt(genes: list[str], risk_group: Optional[str], evidence: list[dict]) -> str:
    lines: list[str] = []
    for e in evidence:
        if e["source"] == "CIViC":
            bits = [f"{e['gene']} → {e['drug']} (CIViC {e.get('evidence_type','')}"]
            if e.get("significance"):
                bits.append(f", {e['significance']}")
            if e.get("direction"):
                bits.append(f", {e['direction']}")
            if e.get("evidence_level"):
                bits.append(f", level {e['evidence_level']}")
            disease = f"; {e['disease']}" if e.get("disease") else ""
            lines.append("".join(bits) + ")" + disease)
        else:
            appr = "approved" if e.get("approved") else "investigational"
            itype = f", {e['interaction_type']}" if e.get("interaction_type") else ""
            lines.append(f"{e['gene']} → {e['drug']} (DGIdb interaction{itype}; {appr})")
    evidence_block = "\n".join(f"- {ln}" for ln in lines)
    rg = f" assigned to the {risk_group}-risk group" if risk_group else ""

    return (
        "A tumour-expression risk model flagged these genes as risk-driving in a "
        f"patient{rg}. Below is DOCUMENTED biomarker–therapy evidence from CIViC and DGIdb "
        f"for those genes:\n{evidence_block}\n\n"
        "Write brief 'treatments to consider and discuss with the tumour board'. Strict requirements:\n"
        "1. Discuss ONLY the drugs/biomarkers in the evidence above, and cite the source "
        "(CIViC/DGIdb) and, for CIViC, the significance (sensitivity/resistance) and level.\n"
        "2. Frame every point as an ADVISORY research suggestion to discuss — do NOT instruct, "
        "prescribe, or tell anyone to administer/start/give a drug. No imperatives.\n"
        "3. State explicitly this is advisory and hypothesis-generating, grounded in documented "
        "evidence; research-use-only; not a prescription and not a guarantee of response.\n"
        "4. If the evidence is sparse or mixed, say so. Do not invent drugs, genes, or claims.\n"
        "5. Under 180 words."
    )


# Evidence-strength ordering used only as a within-gene tiebreaker for which
# drug to check first (a Tier-2 fallback build takes ~2-5 min): CIViC level
# A/B, then approved DGIdb interactions, then everything else. This is NOT an
# eligibility filter — approval/evidence-level status has no bearing on
# whether a matching GEO cohort actually exists, so every drug is checkable.
_CIVIC_LEVEL_RANK = {"A": 0, "B": 1}
_MAX_COHORT_KM_DRUGS = 8


def _select_top_drugs(evidence: list[dict], max_n: int = _MAX_COHORT_KM_DRUGS) -> list[str]:
    """Pick up to `max_n` distinct drug names worth a cohort-KM lookup,
    round-robined across the risk-driving genes so one gene's several
    approved drugs (e.g. HDAC4's several HDAC inhibitors) can't consume the
    whole budget and leave other genes (e.g. NOTCH2, APC) never checked at
    all. Evidence strength only orders candidates within a gene."""
    def rank(e: dict) -> int:
        if e.get("source") == "CIViC":
            return _CIVIC_LEVEL_RANK.get((e.get("evidence_level") or "").upper(), 2)
        return 0 if e.get("approved") else 1

    by_gene: "OrderedDict[str, list[dict]]" = OrderedDict()
    for e in evidence:
        by_gene.setdefault(e["gene"], []).append(e)
    for bucket in by_gene.values():
        bucket.sort(key=rank)

    picked: list[str] = []
    seen: set[str] = set()
    queues = {gene: iter(bucket) for gene, bucket in by_gene.items()}
    while len(picked) < max_n and queues:
        exhausted = []
        for gene, queue in queues.items():
            if len(picked) >= max_n:
                break
            for e in queue:
                key = e["drug"].strip().lower()
                if key in seen:
                    continue
                seen.add(key)
                picked.append(e["drug"])
                break
            else:
                exhausted.append(gene)
        for gene in exhausted:
            queues.pop(gene, None)
    return picked


async def _resolve_cohort_km(
    model, drug: str, cohort_cache: dict
) -> TreatmentKMEvidence:
    """Resolve tiered real-GEO-cohort KM evidence for one suggested drug:
    Tier 1 — true treated-vs-untreated arms within the model's training
    cohort; Tier 2 — a treatment-matched reference cohort (may be
    building); Tier 3 — no matching data. Never fabricates a curve.

    `cohort_cache` memoizes the (LLM-backed) Tier-1 cohort load per accession
    so checking several drugs against the same training accession in one
    request only pays that cost once.

    Also widens the drug-name match with PubChem synonyms (brand names,
    research codes) so a differently-named arm in the same cohort — real
    data we'd otherwise miss on a naming technicality — is still attributed.
    """
    try:
        synonyms = await get_drug_synonym_service().get_synonyms(drug)
    except (ValueError, KeyError, OSError, RuntimeError) as e:
        logger.warning("Drug synonym lookup failed for %s: %s", drug, e)
        synonyms = []

    accession = model.training_accession
    if accession and _signature_service is not None:
        if accession not in cohort_cache:
            try:
                cohort_cache[accession] = await _signature_service.load_cohort_treatment_arms(accession)
            except (ValueError, KeyError, OSError, RuntimeError) as e:
                logger.warning("Tier-1 cohort load failed for %s: %s", accession, e)
                cohort_cache[accession] = None
        loaded = cohort_cache[accession]
        if loaded is not None:
            surv, treatment_binary, arm_names = loaded
            arms = _signature_service.match_treatment_arm_km(
                surv, treatment_binary, arm_names, drug, synonyms=synonyms
            )
            if arms:
                return TreatmentKMEvidence(
                    drug=drug, tier="arm_comparison", accession=accession, arms=arms,
                    n_total=sum(a.n_samples for a in arms), caveat=ARM_COMPARISON_CAVEAT,
                )

    if model.cancer_type:
        try:
            return await get_treatment_service().get_or_build_km_for_drug(
                model.cancer_type, drug, synonyms=synonyms
            )
        except RuntimeError as e:
            logger.warning("Tier-2 cohort lookup unavailable for %s: %s", drug, e)

    return TreatmentKMEvidence(
        drug=drug, tier="unavailable",
        build_error="No matching GEO cohort data available for this drug.",
    )


@router.post("/therapy-rationale", response_model=TherapyRationaleResponse)
async def therapy_rationale(request: TherapyRationaleRequest):
    """Generate grounded advisory 'treatments to consider', anchored to real
    CIViC/DGIdb evidence for the patient's risk-driving genes. Advisory only —
    a prescribing-language guardrail strips any output that reads as a directive,
    and absent evidence yields an honest 'none found' rather than speculation."""
    if _signature_service is None or _therapy_evidence_service is None:
        raise HTTPException(status_code=500, detail="Therapy services not initialized")

    model = _signature_service.get_model(request.model_id)
    if model is None:
        raise HTTPException(status_code=404, detail="Model not found")

    genes = [g.upper() for g in request.genes if g] or [
        g.gene_symbol
        for g in sorted(model.genes, key=lambda x: abs(x.coefficient), reverse=True)[:8]
    ]
    evidence = _therapy_evidence_service.lookup(genes, max_total=40)

    no_evidence_msg = (
        "No documented therapeutic associations were found in CIViC or DGIdb for these "
        "biomarkers. This is common and does not imply the absence of options — discuss "
        "the patient's profile with the care team."
    )
    if not evidence:
        return TherapyRationaleResponse(rationale=no_evidence_msg, evidence=[], domain_score=0)

    prompt = _build_therapy_prompt(genes, request.risk_group, evidence)
    model_name = "anthropic" if request.model == "claude" else request.model
    service = get_pydantic_ai_service()
    try:
        rationale, _tokens, domain_score = await service.generate_response(
            messages=[{"role": "user", "content": prompt}],
            model=model_name,
            conversation_id="therapy-rationale",
        )
    except (RuntimeError, ValueError, ConnectionError) as e:
        logger.warning("Therapy rationale generation failed: %s", e)
        raise HTTPException(status_code=502, detail="Therapy rationale temporarily unavailable")

    # Guardrail: withhold prose that reads as a prescribing directive.
    if _PRESCRIBING_PATTERN.search(rationale):
        logger.warning("Therapy rationale withheld: prescribing-language guardrail triggered")
        rationale = (
            "An AI rationale was withheld because it did not meet the hypothesis-only "
            "guardrail. The documented associations below are provided for tumour-board "
            "discussion."
        )
        domain_score = 0

    records = [TherapyEvidenceRecord(**e) for e in evidence]

    # Auto-build cohort KM evidence for a budget of drugs, round-robined
    # across genes (Tier 1 resolves inline; Tier 2 kicks off a background
    # build and comes back as `is_building` — the frontend polls
    # /therapy-rationale/cohort-km). Every record gets an explicit tier —
    # "not_checked" for drugs outside this round's budget — instead of a
    # silent `None` the UI has no way to explain.
    top_drugs = _select_top_drugs(evidence)
    cohort_cache: dict = {}
    km_by_drug: dict[str, TreatmentKMEvidence] = {}
    for drug in top_drugs:
        try:
            km_by_drug[drug] = await _resolve_cohort_km(model, drug, cohort_cache)
        except (ValueError, KeyError, OSError, RuntimeError) as e:
            logger.warning("Cohort KM resolution failed for drug=%s: %s", drug, e)
    for record in records:
        record.cohort_km = km_by_drug.get(record.drug) or TreatmentKMEvidence(
            drug=record.drug, tier="not_checked",
            build_error="Not checked for GEO cohort data this round.",
        )

    return TherapyRationaleResponse(rationale=rationale, evidence=records, domain_score=domain_score)


class CohortKMRequest(BaseModel):
    """Poll/refresh request for per-drug cohort KM evidence (F24b) — used by
    the frontend while a Tier-2 build is still in progress."""
    model_id: str
    drugs: list[str] = Field(default_factory=list)


class CohortKMResponse(BaseModel):
    results: list[TreatmentKMEvidence]


@router.post("/therapy-rationale/cohort-km", response_model=CohortKMResponse)
async def therapy_rationale_cohort_km(request: CohortKMRequest):
    """Resolve (or re-poll) cohort KM evidence for a batch of drug names
    against an already-built signature model. Idempotent — safe to call
    repeatedly while a Tier-2 cohort model is still building."""
    if _signature_service is None:
        raise HTTPException(status_code=500, detail="Therapy services not initialized")

    model = _signature_service.get_model(request.model_id)
    if model is None:
        raise HTTPException(status_code=404, detail="Model not found")

    drugs = request.drugs[:_MAX_COHORT_KM_DRUGS]
    cohort_cache: dict = {}
    results = []
    for drug in drugs:
        try:
            results.append(await _resolve_cohort_km(model, drug, cohort_cache))
        except (ValueError, KeyError, OSError, RuntimeError) as e:
            logger.warning("Cohort KM resolution failed for drug=%s: %s", drug, e)
            results.append(TreatmentKMEvidence(
                drug=drug, tier="unavailable", build_error="Lookup failed unexpectedly.",
            ))
    return CohortKMResponse(results=results)
