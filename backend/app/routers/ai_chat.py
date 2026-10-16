"""AI Chat, Conversations, and User Feedback Router.

Task ID: S4-API-01, S4-API-03
Exposes:
- GET /ai/conversations: List user conversations
- POST /ai/conversations: Create new conversation session
- GET /ai/conversations/{id}/messages: Fetch message history
- POST /ai/conversations/{id}/messages: Send message and generate RAG-grounded response
- DELETE /ai/conversations/{id}: Delete conversation with owner verification
- POST /ai/feedback: Submit user rating and qualitative feedback
"""

from datetime import datetime, timezone
import uuid
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field

from backend.app.core.envelope import create_response_envelope
from backend.app.core.errors import ForbiddenException, NotFoundException
from backend.app.domain.ai_orchestration import AIOrchestrator
from backend.app.routers.auth import get_current_user_id

router = APIRouter(prefix="/ai", tags=["AI Financial Assistant"])
orchestrator = AIOrchestrator()

# In-memory stores for isolated operational baseline
_CONVERSATION_STORE: Dict[str, Dict] = {}
_MESSAGE_STORE: Dict[str, List[Dict]] = {}
_FEEDBACK_STORE: Dict[str, Dict] = {}


class CreateConversationRequest(BaseModel):
    title: Optional[str] = "Financial Research Session"


class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000, description="User prompt or financial query")


class FeedbackSubmissionRequest(BaseModel):
    message_id: str
    rating: int = Field(..., description="1 for Thumbs Up, -1 for Thumbs Down")
    feedback_type: Optional[str] = Field("helpful", description="'accurate', 'hallucination', 'helpful', 'missing_citation'")
    comments: Optional[str] = None


@router.get("/conversations")
async def list_conversations(
    request: Request,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user_id),
):
    """List caller's conversations with deterministic pagination and isolation."""
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))

    user_convs = [
        c for c in _CONVERSATION_STORE.values()
        if c["user_id"] == user_id and not c.get("is_deleted", False)
    ]
    user_convs.sort(key=lambda x: x["updated_at"], reverse=True)

    # If no conversation exists yet, bootstrap one default conversation
    if not user_convs and offset == 0:
        default_id = "conv-welcome-001"
        now_str = datetime.now(timezone.utc).isoformat()
        default_c = {
            "id": default_id,
            "user_id": user_id,
            "title": "SEBI Guidelines & Asset Allocation",
            "created_at": now_str,
            "updated_at": now_str,
            "is_deleted": False,
        }
        _CONVERSATION_STORE[default_id] = default_c
        user_convs = [default_c]

        # Seed welcome message
        _MESSAGE_STORE[default_id] = [
            {
                "id": "msg-welcome-01",
                "conversation_id": default_id,
                "role": "assistant",
                "headline": "Welcome to Ask FinEx",
                "content": "I am FinEx, your educational financial assistant. Ask me questions regarding financial planning, emergency funds, SIP compounding, diversification, or compare securities.",
                "citations": [],
                "created_at": now_str,
                "correlation_id": cid or "init",
            }
        ]

    paginated = user_convs[offset : offset + limit]

    return create_response_envelope(
        data={
            "conversations": paginated,
            "total": len(user_convs),
            "limit": limit,
            "offset": offset,
        },
        correlation_id=cid,
    )


@router.post("/conversations")
async def create_conversation(
    request: Request,
    payload: CreateConversationRequest,
    current_user: dict = Depends(get_current_user_id),
):
    """Create a new conversational session."""
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))
    now_str = datetime.now(timezone.utc).isoformat()

    conv_id = f"conv-{uuid.uuid4().hex[:12]}"
    conv_data = {
        "id": conv_id,
        "user_id": user_id,
        "title": payload.title or "Financial Research Session",
        "created_at": now_str,
        "updated_at": now_str,
        "is_deleted": False,
    }
    _CONVERSATION_STORE[conv_id] = conv_data
    _MESSAGE_STORE[conv_id] = []

    return create_response_envelope(data=conv_data, correlation_id=cid)


@router.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(
    request: Request,
    conversation_id: str,
    current_user: dict = Depends(get_current_user_id),
):
    """Fetch all messages for caller-owned conversation."""
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))

    conv = _CONVERSATION_STORE.get(conversation_id)
    if not conv or conv.get("is_deleted", False):
        raise NotFoundException(message="Conversation not found.")
    if conv["user_id"] != user_id:
        raise ForbiddenException(message="Forbidden: You do not own this conversation.")

    messages = _MESSAGE_STORE.get(conversation_id, [])

    return create_response_envelope(
        data={"conversation_id": conversation_id, "messages": messages, "total": len(messages)},
        correlation_id=cid,
    )


@router.post("/conversations/{conversation_id}/messages")
async def post_message_to_conversation(
    request: Request,
    conversation_id: str,
    payload: SendMessageRequest,
    current_user: dict = Depends(get_current_user_id),
):
    """Submit user prompt, run RAG orchestration, and persist responses."""
    cid = getattr(request.state, "correlation_id", str(uuid.uuid4()))
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))
    now_str = datetime.now(timezone.utc).isoformat()

    conv = _CONVERSATION_STORE.get(conversation_id)
    if not conv or conv.get("is_deleted", False):
        raise NotFoundException(message="Conversation not found.")
    if conv["user_id"] != user_id:
        raise ForbiddenException(message="Forbidden: You do not own this conversation.")

    # 1. Store user message
    user_msg_id = f"msg-{uuid.uuid4().hex[:12]}"
    user_msg = {
        "id": user_msg_id,
        "conversation_id": conversation_id,
        "role": "user",
        "content": payload.content,
        "created_at": now_str,
        "correlation_id": cid,
    }
    _MESSAGE_STORE.setdefault(conversation_id, []).append(user_msg)

    # 2. Run AI Orchestrator
    ai_resp = await orchestrator.answer_query(
        query=payload.content,
        conversation_id=conversation_id,
        correlation_id=cid,
    )

    # 3. Store assistant message
    asst_msg = {
        "id": ai_resp.message_id,
        "conversation_id": conversation_id,
        "role": "assistant",
        "headline": ai_resp.headline,
        "content": ai_resp.content,
        "intent": ai_resp.intent.value,
        "citations": [c.model_dump(mode="json") for c in ai_resp.citations],
        "model_version": ai_resp.model_version,
        "latency_ms": ai_resp.latency_ms,
        "is_fallback": ai_resp.is_fallback,
        "legal_disclaimer": ai_resp.legal_disclaimer,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "correlation_id": cid,
    }
    _MESSAGE_STORE[conversation_id].append(asst_msg)

    # Update conversation updated_at
    conv["updated_at"] = asst_msg["created_at"]

    return create_response_envelope(data={"user_message": user_msg, "assistant_message": asst_msg}, correlation_id=cid)


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    request: Request,
    conversation_id: str,
    current_user: dict = Depends(get_current_user_id),
):
    """Soft delete a conversation."""
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))

    conv = _CONVERSATION_STORE.get(conversation_id)
    if not conv or conv.get("is_deleted", False):
        raise NotFoundException(message="Conversation not found.")
    if conv["user_id"] != user_id:
        raise ForbiddenException(message="Forbidden: You do not own this conversation.")

    conv["is_deleted"] = True

    return create_response_envelope(
        data={"conversation_id": conversation_id, "deleted": True},
        correlation_id=cid,
    )


@router.post("/feedback")
async def submit_ai_feedback(
    request: Request,
    payload: FeedbackSubmissionRequest,
    current_user: dict = Depends(get_current_user_id),
):
    """Submit user feedback for an AI assistant message."""
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))

    fb_id = f"fb-{uuid.uuid4().hex[:12]}"
    fb_record = {
        "id": fb_id,
        "user_id": user_id,
        "message_id": payload.message_id,
        "rating": payload.rating,
        "feedback_type": payload.feedback_type,
        "comments": payload.comments,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _FEEDBACK_STORE[fb_id] = fb_record

    return create_response_envelope(data=fb_record, correlation_id=cid)
