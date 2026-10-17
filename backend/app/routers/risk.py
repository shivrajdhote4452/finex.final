"""Deterministic Risk Profile Evaluation Router.

Task ID: CH-01, S2-API-02, S2-AI-01
Evaluates risk profiles deterministically based on willingness, capacity, and horizon.
Persists evaluated score and band to user profile upon submission.
"""

from typing import Optional

from backend.app.core.envelope import create_response_envelope
from backend.app.database import get_db
from backend.app.domain.risk import (
    RISK_QUESTIONNAIRE_V1,
    AssessmentSubmission,
    evaluate_risk_profile,
)
from backend.app.domain.user_store import user_store
from backend.app.routers.auth import get_current_user_id
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/risk", tags=["Risk Profile & Assessment"])


@router.get("/questions")
async def get_risk_questionnaire(request: Request):
    """Retrieve versioned risk questionnaire with weighted scoring options."""
    cid = getattr(request.state, "correlation_id", "none")
    return create_response_envelope(RISK_QUESTIONNAIRE_V1, correlation_id=cid)


@router.post("/assessments")
async def submit_risk_assessment(
    request: Request,
    submission: AssessmentSubmission,
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Deterministically score investor answers and generate explanation.
    Persists risk assessment to user profile in PostgreSQL if session token is provided.
    """
    cid = getattr(request.state, "correlation_id", "none")
    result = evaluate_risk_profile(submission)

    # If caller is authenticated, persist assessment against verified identity
    if authorization and authorization.startswith("Bearer "):
        try:
            current_user = await get_current_user_id(authorization, db=db)
            uid = current_user["sub"]
            await user_store.record_risk_assessment_db(uid, result.model_dump(), db=db)
        except HTTPException:
            pass  # Allow unauthenticated demo evaluation if explicitly requested, but do not persist

    return create_response_envelope(result.model_dump(), correlation_id=cid)


@router.get("/assessments/me")
async def get_my_risk_assessment(
    request: Request,
    current_user: dict = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve verified investor's latest saved risk assessment from PostgreSQL."""
    cid = getattr(request.state, "correlation_id", "none")
    uid = current_user["sub"]
    profile = await user_store.get_profile_db(uid, db=db)
    saved = profile.risk_assessment or user_store.get_risk_assessment(uid)
    if not saved:
        return create_response_envelope(
            {
                "has_assessment": False,
                "experience_level": profile.experience_level,
                "risk_band": profile.risk_band,
                "composite_score": profile.composite_score,
            },
            correlation_id=cid,
        )
    return create_response_envelope({"has_assessment": True, **saved}, correlation_id=cid)
