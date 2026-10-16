"""Deterministic Risk Profile Evaluation Router.

Task ID: S2-API-02, S2-AI-01
"""

from backend.app.core.envelope import create_response_envelope
from backend.app.domain.risk import (
    RISK_QUESTIONNAIRE_V1,
    AssessmentSubmission,
    evaluate_risk_profile,
)
from fastapi import APIRouter, Request

router = APIRouter(prefix="/risk", tags=["Risk Profile & Assessment"])


@router.get("/questions")
async def get_risk_questionnaire(request: Request):
    """Retrieve versioned risk questionnaire with weighted scoring options."""
    cid = getattr(request.state, "correlation_id", "none")
    return create_response_envelope(RISK_QUESTIONNAIRE_V1, correlation_id=cid)


@router.post("/assessments")
async def submit_risk_assessment(request: Request, submission: AssessmentSubmission):
    """Deterministically score investor answers and generate explanation."""
    cid = getattr(request.state, "correlation_id", "none")
    result = evaluate_risk_profile(submission)
    return create_response_envelope(result.model_dump(), correlation_id=cid)
