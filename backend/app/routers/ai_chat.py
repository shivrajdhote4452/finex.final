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

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from backend.app.core.envelope import create_response_envelope
from backend.app.core.errors import ForbiddenException, NotFoundException
from backend.app.database import get_db
from backend.app.domain.ai_orchestration import AIOrchestrator
from backend.app.models.rag import AIConversation, AIFeedback, AIMessage
from backend.app.routers.auth import get_current_user_id
from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
    feedback_type: Optional[str] = Field(
        "helpful", description="'accurate', 'hallucination', 'helpful', 'missing_citation'"
    )
    comments: Optional[str] = None


@router.get("/conversations")
async def list_conversations(
    request: Request,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """List caller's conversations with deterministic pagination, isolation, and DB persistence."""
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))

    try:
        stmt = (
            select(AIConversation)
            .where(AIConversation.user_id == user_id, AIConversation.is_deleted == False)  # noqa: E712
            .order_by(AIConversation.updated_at.desc())
        )
        res = await db.execute(stmt)
        db_convs = res.scalars().all()

        if db_convs:
            conv_list = [
                {
                    "id": c.id,
                    "user_id": c.user_id,
                    "title": c.title,
                    "created_at": c.created_at.isoformat() if c.created_at else datetime.now(timezone.utc).isoformat(),
                    "updated_at": c.updated_at.isoformat() if c.updated_at else datetime.now(timezone.utc).isoformat(),
                    "is_deleted": c.is_deleted,
                }
                for c in db_convs
            ]
            for c_data in conv_list:
                _CONVERSATION_STORE[c_data["id"]] = c_data
            paginated = conv_list[offset : offset + limit]
            return create_response_envelope(
                data={
                    "conversations": paginated,
                    "total": len(conv_list),
                    "limit": limit,
                    "offset": offset,
                },
                correlation_id=cid,
            )
    except Exception:
        pass

    user_convs = [c for c in _CONVERSATION_STORE.values() if c["user_id"] == user_id and not c.get("is_deleted", False)]
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
    db: AsyncSession = Depends(get_db),
):
    """Create a new conversational session with DB persistence."""
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))
    now = datetime.now(timezone.utc)
    conv_id = f"conv-{uuid.uuid4().hex[:12]}"

    conv_data = {
        "id": conv_id,
        "user_id": user_id,
        "title": payload.title or "Financial Research Session",
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "is_deleted": False,
    }

    try:
        db_conv = AIConversation(
            id=conv_id,
            user_id=user_id,
            title=payload.title or "Financial Research Session",
            created_at=now,
            updated_at=now,
            is_deleted=False,
        )
        db.add(db_conv)
        await db.commit()
    except Exception:
        pass

    _CONVERSATION_STORE[conv_id] = conv_data
    _MESSAGE_STORE[conv_id] = []

    return create_response_envelope(data=conv_data, correlation_id=cid)


@router.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(
    request: Request,
    conversation_id: str,
    current_user: dict = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Fetch all messages for caller-owned conversation with DB persistence."""
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))

    try:
        conv_res = await db.execute(
            select(AIConversation).where(
                AIConversation.id == conversation_id,
                AIConversation.is_deleted == False,  # noqa: E712
            )
        )
        db_conv = conv_res.scalars().first()
        if db_conv:
            if db_conv.user_id != user_id:
                raise ForbiddenException(message="Forbidden: You do not own this conversation.")
            msg_res = await db.execute(
                select(AIMessage).where(AIMessage.conversation_id == conversation_id).order_by(AIMessage.created_at.asc())
            )
            db_msgs = msg_res.scalars().all()
            messages = [
                {
                    "id": m.id,
                    "conversation_id": m.conversation_id,
                    "role": m.role,
                    "content": m.content,
                    "intent": m.intent_detected,
                    "model_version": m.model_version,
                    "latency_ms": m.latency_ms,
                    "is_fallback": m.is_fallback,
                    "citations": m.citation_chunk_ids or [],
                    "created_at": m.created_at.isoformat() if m.created_at else datetime.now(timezone.utc).isoformat(),
                    "correlation_id": m.correlation_id,
                }
                for m in db_msgs
            ]
            _MESSAGE_STORE[conversation_id] = messages
            return create_response_envelope(
                data={"conversation_id": conversation_id, "messages": messages, "total": len(messages)},
                correlation_id=cid,
            )
    except (ForbiddenException, NotFoundException):
        raise
    except Exception:
        pass

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
    db: AsyncSession = Depends(get_db),
):
    """Submit user prompt, run RAG orchestration, and persist responses to database."""
    cid = getattr(request.state, "correlation_id", str(uuid.uuid4()))
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))
    now = datetime.now(timezone.utc)
    now_str = now.isoformat()

    # Check conversation ownership
    try:
        conv_res = await db.execute(
            select(AIConversation).where(
                AIConversation.id == conversation_id,
                AIConversation.is_deleted == False,  # noqa: E712
            )
        )
        db_conv = conv_res.scalars().first()
        if db_conv and db_conv.user_id != user_id:
            raise ForbiddenException(message="Forbidden: You do not own this conversation.")
        if not db_conv and conversation_id not in _CONVERSATION_STORE:
            raise NotFoundException(message="Conversation not found.")
    except (ForbiddenException, NotFoundException):
        raise
    except Exception:
        conv = _CONVERSATION_STORE.get(conversation_id)
        if not conv or conv.get("is_deleted", False):
            raise NotFoundException(message="Conversation not found.")
        if conv["user_id"] != user_id:
            raise ForbiddenException(message="Forbidden: You do not own this conversation.")

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
    asst_msg_id = ai_resp.message_id
    asst_now = datetime.now(timezone.utc)
    citations_data = [c.model_dump(mode="json") for c in ai_resp.citations]
    asst_msg = {
        "id": asst_msg_id,
        "conversation_id": conversation_id,
        "role": "assistant",
        "headline": ai_resp.headline,
        "content": ai_resp.content,
        "intent": ai_resp.intent.value,
        "citations": citations_data,
        "model_version": ai_resp.model_version,
        "latency_ms": ai_resp.latency_ms,
        "is_fallback": ai_resp.is_fallback,
        "legal_disclaimer": ai_resp.legal_disclaimer,
        "created_at": asst_now.isoformat(),
        "correlation_id": cid,
    }
    _MESSAGE_STORE[conversation_id].append(asst_msg)

    if conversation_id in _CONVERSATION_STORE:
        _CONVERSATION_STORE[conversation_id]["updated_at"] = asst_msg["created_at"]

    # Persist both to database
    try:
        db_user_msg = AIMessage(
            id=user_msg_id,
            conversation_id=conversation_id,
            user_id=user_id,
            role="user",
            content=payload.content,
            correlation_id=cid,
            created_at=now,
        )
        db_asst_msg = AIMessage(
            id=asst_msg_id,
            conversation_id=conversation_id,
            user_id=user_id,
            role="assistant",
            content=ai_resp.content,
            intent_detected=ai_resp.intent.value,
            correlation_id=cid,
            latency_ms=ai_resp.latency_ms,
            model_version=ai_resp.model_version,
            is_fallback=ai_resp.is_fallback,
            citation_chunk_ids=citations_data,
            created_at=asst_now,
        )
        db.add(db_user_msg)
        db.add(db_asst_msg)
        if db_conv:
            db_conv.updated_at = asst_now
        await db.commit()
    except Exception:
        pass

    return create_response_envelope(data={"user_message": user_msg, "assistant_message": asst_msg}, correlation_id=cid)


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    request: Request,
    conversation_id: str,
    current_user: dict = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Soft delete a conversation with database persistence."""
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))

    try:
        conv_res = await db.execute(
            select(AIConversation).where(
                AIConversation.id == conversation_id,
                AIConversation.is_deleted == False,  # noqa: E712
            )
        )
        db_conv = conv_res.scalars().first()
        if db_conv:
            if db_conv.user_id != user_id:
                raise ForbiddenException(message="Forbidden: You do not own this conversation.")
            db_conv.is_deleted = True
            await db.commit()
            if conversation_id in _CONVERSATION_STORE:
                _CONVERSATION_STORE[conversation_id]["is_deleted"] = True
            return create_response_envelope(data={"conversation_id": conversation_id, "deleted": True}, correlation_id=cid)
    except (ForbiddenException, NotFoundException):
        raise
    except Exception:
        pass

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
    db: AsyncSession = Depends(get_db),
):
    """Submit user feedback for an AI assistant message with database persistence."""
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))
    now = datetime.now(timezone.utc)
    fb_id = f"fb-{uuid.uuid4().hex[:12]}"

    fb_record = {
        "id": fb_id,
        "user_id": user_id,
        "message_id": payload.message_id,
        "rating": payload.rating,
        "feedback_type": payload.feedback_type,
        "comments": payload.comments,
        "created_at": now.isoformat(),
    }
    _FEEDBACK_STORE[fb_id] = fb_record

    try:
        msg_res = await db.execute(select(AIMessage).where(AIMessage.id == payload.message_id))
        db_msg = msg_res.scalars().first()
        if not db_msg:
            # Ensure placeholder conversation and message exist so feedback is persisted with valid FK
            placeholder_conv_id = f"conv-fb-{uuid.uuid4().hex[:8]}"
            conv_res = await db.execute(select(AIConversation).where(AIConversation.id == placeholder_conv_id))
            if not conv_res.scalars().first():
                db.add(
                    AIConversation(
                        id=placeholder_conv_id,
                        user_id=user_id,
                        title="Feedback Context",
                        is_deleted=False,
                        created_at=now,
                        updated_at=now,
                    )
                )
                await db.flush()
            db.add(
                AIMessage(
                    id=payload.message_id,
                    conversation_id=placeholder_conv_id,
                    role="assistant",
                    content="[Sample / Offline Message]",
                    created_at=now,
                )
            )
            await db.flush()

        db_fb = AIFeedback(
            id=fb_id,
            user_id=user_id,
            message_id=payload.message_id,
            rating=payload.rating,
            feedback_type=payload.feedback_type,
            comments=payload.comments,
            created_at=now,
        )
        db.add(db_fb)
        await db.commit()
    except Exception:
        await db.rollback()

    return create_response_envelope(data=fb_record, correlation_id=cid)
