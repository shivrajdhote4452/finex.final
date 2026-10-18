"""Gemini Investment Assistant API Router.

Exposes:
- POST /ai/assistant/chat: Send user query in English/Hindi/Hinglish with chart context
- GET /ai/assistant/proposals: Fetch user's pending paper allocation proposals
- POST /ai/assistant/proposals/{proposal_id}/execute: Authorize and execute a proposal
- GET /ai/assistant/status: Check AI setup status (model, configured state)
"""

from typing import Any, Dict, Optional

from backend.app.core.envelope import create_response_envelope
from backend.app.database import get_db
from backend.app.domain.gemini_assistant import (
    SIMULATION_DISCLAIMER,
    gemini_assistant,
)
from backend.app.models.paper_trading import PaperProposal
from backend.app.routers.auth import get_current_user_id
from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/ai/assistant", tags=["Gemini Paper Investment Assistant"])


class AssistantChatRequest(BaseModel):
    message: str = Field(
        ..., min_length=1, max_length=2000, description="User instruction or question in English, Hindi, or Hinglish"
    )
    conversation_id: Optional[str] = None
    active_chart_context: Optional[Dict[str, Any]] = None
    chart_context: Optional[Dict[str, Any]] = None


@router.get("/status")
async def get_assistant_status(request: Request):
    """Check AI assistant configuration state without leaking API keys."""
    cid = getattr(request.state, "correlation_id", None)
    has_live = gemini_assistant.is_gemini_api_ready()

    return create_response_envelope(
        data={
            "is_configured": True,
            "has_live_gemini": has_live,
            "model": gemini_assistant.settings.GEMINI_MODEL,
            "provider": "gemini-live" if has_live else "mock-offline",
            "status_message": (
                "Gemini AI Assistant is active and connected to Google Gemini API."
                if has_live
                else "FinEx AI Paper Assistant is active in intelligent simulation mode."
            ),
            "disclaimer": SIMULATION_DISCLAIMER,
        },
        correlation_id=cid,
    )


@router.post("/chat")
async def chat_with_assistant(
    request: Request,
    payload: AssistantChatRequest,
    current_user: dict = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Chat with Gemini investment assistant with grounded tool execution."""
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))

    chart_ctx = payload.active_chart_context or payload.chart_context
    result = await gemini_assistant.process_user_turn(
        user_id=user_id,
        user_message=payload.message,
        conversation_id=payload.conversation_id,
        db=db,
        active_chart_context=chart_ctx,
    )

    return create_response_envelope(data=result.model_dump(mode="json"), correlation_id=cid)


@router.get("/proposals")
async def list_user_proposals(
    request: Request,
    limit: int = Query(10, ge=1, le=50),
    current_user: dict = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """List pending and historical paper proposals for caller."""
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))

    stmt = (
        select(PaperProposal)
        .where(PaperProposal.user_id == user_id)
        .order_by(desc(PaperProposal.created_at))
        .limit(limit)
    )
    res = await db.execute(stmt)
    proposals = res.scalars().all()

    return create_response_envelope(
        data={
            "proposals": [
                {
                    "id": p.id,
                    "instruction_text": p.instruction_text,
                    "proposed_allocations": p.proposed_allocations,
                    "total_budget": float(p.total_budget),
                    "currency": p.currency,
                    "status": p.status,
                    "created_at": p.created_at.isoformat() if p.created_at else None,
                    "expires_at": p.expires_at.isoformat() if p.expires_at else None,
                    "executed_at": p.executed_at.isoformat() if p.executed_at else None,
                    "receipts": p.execution_receipts,
                }
                for p in proposals
            ],
            "total": len(proposals),
        },
        correlation_id=cid,
    )


@router.post("/proposals/{proposal_id}/execute")
async def execute_proposal(
    request: Request,
    proposal_id: str,
    current_user: dict = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Explicitly authorize and execute an unexpired paper allocation proposal."""
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))

    result = await gemini_assistant.tool_execute_paper_proposal(user_id, proposal_id, db=db)
    return create_response_envelope(data=result, correlation_id=cid)
