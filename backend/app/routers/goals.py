"""Financial Goals API Router.

Task ID: S7-API-01
Author: Shivraj Dhote
Date: 16 October 2026

Exposes:
- POST /goals: Create financial goal with deterministic return assumptions
- GET /goals: List user's active/all financial goals
- GET /goals/{goal_id}: Retrieve single goal details
- PATCH /goals/{goal_id}: Update target amount or return assumptions
- POST /goals/{goal_id}/contributions: Record contribution toward goal
- GET /goals/{goal_id}/projection: Return mathematical FV, required monthly contribution, and gap
"""

from backend.app.core.envelope import create_response_envelope
from backend.app.domain.goal_engine import (
    ContributionCreate,
    GoalCreate,
    GoalEngine,
    GoalUpdate,
)
from backend.app.routers.auth import get_current_user_id
from fastapi import APIRouter, Depends, HTTPException, Request, status

router = APIRouter(prefix="/goals", tags=["Financial Goals & Planning"])
goal_engine = GoalEngine()


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_financial_goal(
    request: Request,
    payload: GoalCreate,
    current_user: dict = Depends(get_current_user_id),
):
    """Create a new financial goal with deterministic projection validation."""
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))

    try:
        goal = goal_engine.create_goal(user_id, payload)
        return create_response_envelope(data=goal, correlation_id=cid)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.get("")
async def list_financial_goals(
    request: Request,
    current_user: dict = Depends(get_current_user_id),
):
    """List financial goals configured by user."""
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))

    goals = goal_engine.get_user_goals(user_id)
    return create_response_envelope(data={"goals": goals, "total": len(goals)}, correlation_id=cid)


@router.get("/{goal_id}")
async def get_financial_goal(
    goal_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user_id),
):
    """Retrieve details for a single financial goal."""
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))

    goal = goal_engine.get_goal_by_id(user_id, goal_id)
    if not goal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Goal {goal_id} not found.")
    return create_response_envelope(data=goal, correlation_id=cid)


@router.patch("/{goal_id}")
async def update_financial_goal(
    goal_id: str,
    request: Request,
    payload: GoalUpdate,
    current_user: dict = Depends(get_current_user_id),
):
    """Update goal parameters."""
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))

    try:
        updated = goal_engine.update_goal(user_id, goal_id, payload)
        return create_response_envelope(data=updated, correlation_id=cid)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Goal {goal_id} not found.")


@router.post("/{goal_id}/contributions")
async def record_goal_contribution(
    goal_id: str,
    request: Request,
    payload: ContributionCreate,
    current_user: dict = Depends(get_current_user_id),
):
    """Record an append-only cash deposit towards goal."""
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))

    try:
        res = goal_engine.record_contribution(user_id, goal_id, payload)
        return create_response_envelope(data=res, correlation_id=cid)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Goal {goal_id} not found.")


@router.get("/{goal_id}/projection")
async def get_goal_projection(
    goal_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user_id),
):
    """Calculate deterministic future value projection and required monthly contribution."""
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))

    try:
        proj = goal_engine.get_goal_projection(user_id, goal_id)
        return create_response_envelope(data=proj.model_dump(mode="json"), correlation_id=cid)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Goal {goal_id} not found.")
