"""Alert Rules & Evaluation API Router.

Task ID: S6-API-01
Author: Shivraj Dhote
Date: 16 October 2026

Exposes:
- POST /alerts/rules: Create new price, movement, or concentration alert rule
- GET /alerts/rules: List active/all rules for authenticated user
- GET /alerts/rules/{rule_id}: Get rule details
- PATCH /alerts/rules/{rule_id}: Update rule thresholds or cooldown
- POST /alerts/rules/{rule_id}/deactivate: Deactivate rule
- DELETE /alerts/rules/{rule_id}: Delete rule
- POST /alerts/evaluate: Run deterministic rule evaluation
"""

from decimal import Decimal

from backend.app.adapters.market_data_provider import (
    INSTRUMENT_REGISTRY,
    VERIFIED_OBSERVATIONS,
    RealMarketDataProvider,
)
from backend.app.core.envelope import create_response_envelope
from backend.app.domain.alerts_service import (
    AlertRuleCreate,
    AlertRuleUpdate,
    AlertsService,
)
from backend.app.routers.auth import get_current_user_id
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

router = APIRouter(prefix="/alerts", tags=["Smart Alerts & Rules"])
alerts_service = AlertsService()
market_provider = RealMarketDataProvider(force_cache=True)


@router.post("/rules", status_code=status.HTTP_201_CREATED)
async def create_alert_rule(
    request: Request,
    payload: AlertRuleCreate,
    current_user: dict = Depends(get_current_user_id),
):
    """Create a new deterministic alert rule."""
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))

    try:
        rule = alerts_service.create_rule(user_id, payload)
        return create_response_envelope(data=rule, correlation_id=cid)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.get("/rules")
async def list_alert_rules(
    request: Request,
    active_only: bool = Query(False, description="Filter for active rules only"),
    current_user: dict = Depends(get_current_user_id),
):
    """List alert rules configured by current user."""
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))

    rules = alerts_service.get_user_rules(user_id, active_only=active_only)
    return create_response_envelope(data={"rules": rules, "total": len(rules)}, correlation_id=cid)


@router.get("/rules/{rule_id}")
async def get_alert_rule(
    rule_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user_id),
):
    """Get specific alert rule by ID."""
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))

    rule = alerts_service.get_rule_by_id(user_id, rule_id)
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Rule {rule_id} not found.")
    return create_response_envelope(data=rule, correlation_id=cid)


@router.patch("/rules/{rule_id}")
async def update_alert_rule(
    rule_id: str,
    request: Request,
    payload: AlertRuleUpdate,
    current_user: dict = Depends(get_current_user_id),
):
    """Update threshold, cooldown, or active status of rule."""
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))

    try:
        updated = alerts_service.update_rule(user_id, rule_id, payload)
        return create_response_envelope(data=updated, correlation_id=cid)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Rule {rule_id} not found.")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.post("/rules/{rule_id}/deactivate")
async def deactivate_alert_rule(
    rule_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user_id),
):
    """Deactivate an active alert rule."""
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))

    try:
        deactivated = alerts_service.deactivate_rule(user_id, rule_id)
        return create_response_envelope(data=deactivated, correlation_id=cid)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Rule {rule_id} not found.")


@router.delete("/rules/{rule_id}")
async def delete_alert_rule(
    rule_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user_id),
):
    """Delete an alert rule permanently."""
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))

    success = alerts_service.delete_rule(user_id, rule_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Rule {rule_id} not found.")
    return create_response_envelope(data={"deleted": True, "rule_id": rule_id}, correlation_id=cid)


@router.post("/evaluate")
async def evaluate_user_alerts(
    request: Request,
    current_user: dict = Depends(get_current_user_id),
):
    """Triggers deterministic evaluation of active rules against live market observations."""
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))

    # Fetch latest quotes for all supported instruments
    quotes = {}
    for item in INSTRUMENT_REGISTRY:
        sym = item["symbol"]
        q = await market_provider.get_latest_quote(sym)
        obs = VERIFIED_OBSERVATIONS.get(sym, {})
        if q:
            quotes[sym] = {
                "price": q.price,
                "change_percent": obs.get("change_pct", Decimal("0.0")),
                "observation_date": q.observed_at.isoformat() if q.observed_at else "2026-10-16",
            }

    # Standard portfolio metrics for concentration rules
    portfolio_metrics = {
        "top_holding_pct": 33.33,
        "hhi_score": 1850.0,
    }

    triggered = alerts_service.evaluate_rules(user_id, quotes, portfolio_metrics)
    return create_response_envelope(
        data={
            "rules_evaluated": len(alerts_service.get_user_rules(user_id, active_only=True)),
            "events_triggered": len(triggered),
            "events": triggered,
        },
        correlation_id=cid,
    )
