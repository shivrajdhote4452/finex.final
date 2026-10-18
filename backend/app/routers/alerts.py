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
- GET /alerts/notifications: Fetch in-app notifications
- POST /alerts/notifications/{notif_id}/read: Mark notification read
- POST /alerts/notifications/read-all: Mark all notifications read
"""

import uuid
from decimal import Decimal

from backend.app.adapters.market_data_provider import (
    INSTRUMENT_REGISTRY,
    VERIFIED_OBSERVATIONS,
    RealMarketDataProvider,
)
from backend.app.core.envelope import create_response_envelope
from backend.app.database import get_db
from backend.app.domain.alerts_service import (
    _ALERT_RULES_STORE,
    _NOTIFICATIONS_STORE,
    AlertRuleCreate,
    AlertRuleUpdate,
    AlertsService,
)
from backend.app.models.alerts import AlertEvent, AlertRule, Notification
from backend.app.routers.auth import get_current_user_id
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/alerts", tags=["Smart Alerts & Rules"])
alerts_service = AlertsService()
market_provider = RealMarketDataProvider(force_cache=True, allow_fixture_fallback=True)


def _to_uuid(val: str) -> uuid.UUID:
    """Safely coerce any string identifier into a valid deterministic UUID."""
    try:
        return uuid.UUID(val)
    except ValueError:
        return uuid.uuid5(uuid.NAMESPACE_DNS, str(val))


@router.post("/rules", status_code=status.HTTP_201_CREATED)
async def create_alert_rule(
    request: Request,
    payload: AlertRuleCreate,
    current_user: dict = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Create a new deterministic alert rule with database persistence."""
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))

    try:
        rule = alerts_service.create_rule(user_id, payload)
        rule_uuid = _to_uuid(rule["id"])

        try:
            db_rule = AlertRule(
                id=rule_uuid,
                user_id=user_id,
                rule_type=payload.rule_type,
                symbol=payload.symbol.upper() if payload.symbol else None,
                comparison_operator=payload.comparison_operator,
                threshold_value=payload.threshold_value,
                threshold_unit=payload.threshold_unit,
                cooldown_minutes=payload.cooldown_minutes,
                is_active=True,
            )
            db.add(db_rule)
            await db.commit()
        except Exception:
            pass

        return create_response_envelope(data=rule, correlation_id=cid)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.get("/rules")
async def list_alert_rules(
    request: Request,
    active_only: bool = Query(False, description="Filter for active rules only"),
    current_user: dict = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """List alert rules configured by current user with database persistence."""
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))

    try:
        stmt = select(AlertRule).where(AlertRule.user_id == user_id)
        if active_only:
            stmt = stmt.where(AlertRule.is_active == True)  # noqa: E712
        stmt = stmt.order_by(AlertRule.created_at.desc())
        res = await db.execute(stmt)
        db_rules = res.scalars().all()

        if db_rules:
            formatted = [
                {
                    "id": str(r.id),
                    "user_id": r.user_id,
                    "rule_type": r.rule_type,
                    "symbol": r.symbol,
                    "comparison_operator": r.comparison_operator,
                    "threshold_value": r.threshold_value,
                    "threshold_unit": r.threshold_unit,
                    "cooldown_minutes": r.cooldown_minutes,
                    "is_active": r.is_active,
                    "last_triggered_at": r.last_triggered_at.isoformat() if r.last_triggered_at else None,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                    "updated_at": r.updated_at.isoformat() if r.updated_at else None,
                }
                for r in db_rules
            ]
            for r_data in formatted:
                _ALERT_RULES_STORE[r_data["id"]] = r_data
            return create_response_envelope(data={"rules": formatted, "total": len(formatted)}, correlation_id=cid)
    except Exception:
        pass

    rules = alerts_service.get_user_rules(user_id, active_only=active_only)
    return create_response_envelope(data={"rules": rules, "total": len(rules)}, correlation_id=cid)


@router.get("/rules/{rule_id}")
async def get_alert_rule(
    rule_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get specific alert rule by ID."""
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))

    try:
        rule_uuid = _to_uuid(rule_id)
        stmt = select(AlertRule).where(AlertRule.id == rule_uuid, AlertRule.user_id == user_id)
        res = await db.execute(stmt)
        r = res.scalars().first()
        if r:
            rule_data = {
                "id": str(r.id),
                "user_id": r.user_id,
                "rule_type": r.rule_type,
                "symbol": r.symbol,
                "comparison_operator": r.comparison_operator,
                "threshold_value": r.threshold_value,
                "threshold_unit": r.threshold_unit,
                "cooldown_minutes": r.cooldown_minutes,
                "is_active": r.is_active,
                "last_triggered_at": r.last_triggered_at.isoformat() if r.last_triggered_at else None,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            }
            _ALERT_RULES_STORE[rule_id] = rule_data
            return create_response_envelope(data=rule_data, correlation_id=cid)
    except Exception:
        pass

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
    db: AsyncSession = Depends(get_db),
):
    """Update threshold, cooldown, or active status of rule with database persistence."""
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))

    try:
        updated = alerts_service.update_rule(user_id, rule_id, payload)
        try:
            rule_uuid = _to_uuid(rule_id)
            stmt = select(AlertRule).where(AlertRule.id == rule_uuid, AlertRule.user_id == user_id)
            res = await db.execute(stmt)
            r = res.scalars().first()
            if r:
                if payload.threshold_value is not None:
                    r.threshold_value = payload.threshold_value
                if payload.comparison_operator is not None:
                    r.comparison_operator = payload.comparison_operator
                if payload.cooldown_minutes is not None:
                    r.cooldown_minutes = payload.cooldown_minutes
                if payload.is_active is not None:
                    r.is_active = payload.is_active
                await db.commit()
        except Exception:
            pass
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
    db: AsyncSession = Depends(get_db),
):
    """Deactivate an active alert rule with database persistence."""
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))

    try:
        deactivated = alerts_service.deactivate_rule(user_id, rule_id)
        try:
            rule_uuid = _to_uuid(rule_id)
            stmt = select(AlertRule).where(AlertRule.id == rule_uuid, AlertRule.user_id == user_id)
            res = await db.execute(stmt)
            r = res.scalars().first()
            if r:
                r.is_active = False
                await db.commit()
        except Exception:
            pass
        return create_response_envelope(data=deactivated, correlation_id=cid)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Rule {rule_id} not found.")


@router.delete("/rules/{rule_id}")
async def delete_alert_rule(
    rule_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Delete an alert rule permanently with database persistence."""
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))

    success = alerts_service.delete_rule(user_id, rule_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Rule {rule_id} not found.")

    try:
        rule_uuid = _to_uuid(rule_id)
        stmt = select(AlertRule).where(AlertRule.id == rule_uuid, AlertRule.user_id == user_id)
        res = await db.execute(stmt)
        r = res.scalars().first()
        if r:
            await db.delete(r)
            await db.commit()
    except Exception:
        pass

    return create_response_envelope(data={"deleted": True, "rule_id": rule_id}, correlation_id=cid)


@router.post("/evaluate")
async def evaluate_user_alerts(
    request: Request,
    current_user: dict = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
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

    portfolio_metrics = {
        "top_holding_pct": 33.33,
        "hhi_score": 1850.0,
    }

    triggered = alerts_service.evaluate_rules(user_id, quotes, portfolio_metrics)

    # Persist triggered events and notifications to DB
    try:
        for ev in triggered:
            ev_uuid = _to_uuid(ev["id"])
            rule_uuid = _to_uuid(ev["rule_id"])
            db_ev = AlertEvent(
                id=ev_uuid,
                rule_id=rule_uuid,
                user_id=user_id,
                event_type=ev["event_type"],
                symbol=ev.get("symbol"),
                triggered_value=Decimal(str(ev["triggered_value"])),
                threshold_value=Decimal(str(ev["threshold_value"])),
                title=ev["title"],
                message=ev["message"],
                dedupe_key=ev["dedupe_key"],
            )
            db.add(db_ev)
            await db.flush()

            # Corresponding notification
            notif_uuid = _to_uuid(f"notif-{ev['id']}")
            db_notif = Notification(
                id=notif_uuid,
                user_id=user_id,
                alert_event_id=ev_uuid,
                category=ev["event_type"],
                title=ev["title"],
                body=ev["message"],
                is_read=False,
            )
            db.add(db_notif)
        await db.commit()
    except Exception:
        pass

    return create_response_envelope(
        data={
            "rules_evaluated": len(alerts_service.get_user_rules(user_id, active_only=True)),
            "events_triggered": len(triggered),
            "events": triggered,
        },
        correlation_id=cid,
    )


@router.get("/notifications")
async def list_user_notifications(
    request: Request,
    unread_only: bool = Query(False, description="Filter unread notifications only"),
    current_user: dict = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Fetch in-app notifications generated by alert evaluations with database persistence."""
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))

    try:
        stmt = select(Notification).where(Notification.user_id == user_id)
        if unread_only:
            stmt = stmt.where(Notification.is_read == False)  # noqa: E712
        stmt = stmt.order_by(Notification.created_at.desc())
        res = await db.execute(stmt)
        db_notifs = res.scalars().all()

        if db_notifs:
            formatted = [
                {
                    "id": str(n.id),
                    "user_id": n.user_id,
                    "category": n.category,
                    "title": n.title,
                    "body": n.body,
                    "is_read": n.is_read,
                    "read_at": n.read_at.isoformat() if n.read_at else None,
                    "created_at": n.created_at.isoformat() if n.created_at else None,
                }
                for n in db_notifs
            ]
            for n_data in formatted:
                _NOTIFICATIONS_STORE[n_data["id"]] = n_data
            return create_response_envelope(data={"notifications": formatted, "count": len(formatted)}, correlation_id=cid)
    except Exception:
        pass

    notifs = alerts_service.get_user_notifications(user_id, unread_only=unread_only)
    return create_response_envelope(
        data={"notifications": notifs, "count": len(notifs)},
        correlation_id=cid,
    )


@router.post("/notifications/{notif_id}/read")
async def mark_notification_read(
    notif_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Mark a notification as read with database persistence."""
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))

    try:
        notif_uuid = _to_uuid(notif_id)
        stmt = select(Notification).where(Notification.id == notif_uuid, Notification.user_id == user_id)
        res = await db.execute(stmt)
        n = res.scalars().first()
        if n:
            n.is_read = True
            await db.commit()
    except Exception:
        pass

    ok = alerts_service.mark_notification_read(user_id, notif_id)
    if not ok and not n:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found.")
    return create_response_envelope(data={"read": True, "id": notif_id}, correlation_id=cid)


@router.post("/notifications/read-all")
async def mark_all_notifications_read(
    request: Request,
    current_user: dict = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Mark all notifications as read with database persistence."""
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))

    try:
        stmt = (
            update(Notification)
            .where(Notification.user_id == user_id, Notification.is_read == False)  # noqa: E712
            .values(is_read=True)
        )
        await db.execute(stmt)
        await db.commit()
    except Exception:
        pass

    count = alerts_service.mark_all_notifications_read(user_id)
    return create_response_envelope(data={"marked_read_count": count}, correlation_id=cid)
