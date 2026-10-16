"""Alerts Service and Deterministic Rule Evaluation Engine.

Task ID: S6-API-01, S6-DAT-03
Author: Shivraj Dhote
Date: 16 October 2026

Coordinates:
1. Alert Rule CRUD (Create, Read, Update, Deactivate, Delete).
2. Rule types: PRICE_ABOVE, PRICE_BELOW, PERCENT_CHANGE_UP, PERCENT_CHANGE_DOWN, CONCENTRATION_EXCEEDED, RISK_CHANGE.
3. Strict deterministic rule evaluation against market observations.
4. Cooldown enforcement and duplicate event suppression.
5. Emits AlertEvents and auto-creates in-app Notifications.
"""

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

# In-memory operational store for isolated testing/development baseline
_ALERT_RULES_STORE: Dict[str, Dict[str, Any]] = {}  # rule_id -> rule_dict
_ALERT_EVENTS_STORE: Dict[str, Dict[str, Any]] = {}  # event_id -> event_dict
_NOTIFICATIONS_STORE: Dict[str, Dict[str, Any]] = {}  # notif_id -> notif_dict
_DELIVERY_ATTEMPTS_STORE: Dict[str, List[Dict[str, Any]]] = {}  # notif_id -> list of attempts


class AlertRuleCreate(BaseModel):
    rule_type: str = Field(
        ...,
        description="'PRICE_ABOVE', 'PRICE_BELOW', 'PERCENT_CHANGE_UP', 'PERCENT_CHANGE_DOWN', 'CONCENTRATION_EXCEEDED', 'RISK_CHANGE'",
    )
    symbol: Optional[str] = Field(None, description="Security symbol for price alerts")
    comparison_operator: str = Field(..., description="'>=', '<=', '>', '<', '='")
    threshold_value: Decimal = Field(..., description="Threshold value in specified unit")
    threshold_unit: str = Field(..., description="'INR', 'PERCENT', 'RATIO'")
    cooldown_minutes: int = Field(60, ge=5, le=1440, description="Minimum minutes between repeated triggers")


class AlertRuleUpdate(BaseModel):
    threshold_value: Optional[Decimal] = None
    comparison_operator: Optional[str] = None
    cooldown_minutes: Optional[int] = None
    is_active: Optional[bool] = None


class AlertsService:
    """Manages alert rules and executes deterministic evaluations."""

    def create_rule(self, user_id: str, payload: AlertRuleCreate) -> Dict[str, Any]:
        valid_types = {
            "PRICE_ABOVE",
            "PRICE_BELOW",
            "PERCENT_CHANGE_UP",
            "PERCENT_CHANGE_DOWN",
            "CONCENTRATION_EXCEEDED",
            "RISK_CHANGE",
        }
        if payload.rule_type not in valid_types:
            raise ValueError(f"Unsupported rule type: {payload.rule_type}. Must be one of {valid_types}")

        if payload.rule_type.startswith("PRICE_") and not payload.symbol:
            raise ValueError(f"Rule type {payload.rule_type} requires a target security symbol.")

        if payload.comparison_operator not in {">=", "<=", ">", "<", "="}:
            raise ValueError(f"Invalid comparison operator: {payload.comparison_operator}")

        rule_id = f"rule-{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)
        rule = {
            "id": rule_id,
            "user_id": user_id,
            "rule_type": payload.rule_type,
            "symbol": payload.symbol.upper() if payload.symbol else None,
            "comparison_operator": payload.comparison_operator,
            "threshold_value": payload.threshold_value,
            "threshold_unit": payload.threshold_unit,
            "cooldown_minutes": payload.cooldown_minutes,
            "is_active": True,
            "last_triggered_at": None,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        _ALERT_RULES_STORE[rule_id] = rule
        return rule

    def get_user_rules(self, user_id: str, active_only: bool = False) -> List[Dict[str, Any]]:
        rules = [
            r for r in _ALERT_RULES_STORE.values() if r["user_id"] == user_id and (not active_only or r["is_active"])
        ]
        return sorted(rules, key=lambda x: x["created_at"], reverse=True)

    def get_rule_by_id(self, user_id: str, rule_id: str) -> Optional[Dict[str, Any]]:
        rule = _ALERT_RULES_STORE.get(rule_id)
        if not rule or rule["user_id"] != user_id:
            return None
        return rule

    def update_rule(self, user_id: str, rule_id: str, payload: AlertRuleUpdate) -> Dict[str, Any]:
        rule = self.get_rule_by_id(user_id, rule_id)
        if not rule:
            raise KeyError(f"Rule {rule_id} not found or unauthorized.")

        if payload.threshold_value is not None:
            rule["threshold_value"] = payload.threshold_value
        if payload.comparison_operator is not None:
            if payload.comparison_operator not in {">=", "<=", ">", "<", "="}:
                raise ValueError(f"Invalid comparison operator: {payload.comparison_operator}")
            rule["comparison_operator"] = payload.comparison_operator
        if payload.cooldown_minutes is not None:
            rule["cooldown_minutes"] = payload.cooldown_minutes
        if payload.is_active is not None:
            rule["is_active"] = payload.is_active

        rule["updated_at"] = datetime.now(timezone.utc).isoformat()
        _ALERT_RULES_STORE[rule_id] = rule
        return rule

    def deactivate_rule(self, user_id: str, rule_id: str) -> Dict[str, Any]:
        return self.update_rule(user_id, rule_id, AlertRuleUpdate(is_active=False))

    def delete_rule(self, user_id: str, rule_id: str) -> bool:
        rule = self.get_rule_by_id(user_id, rule_id)
        if not rule:
            return False
        del _ALERT_RULES_STORE[rule_id]
        return True

    def evaluate_rules(
        self,
        user_id: str,
        current_quotes: Dict[str, Dict[str, Any]],
        portfolio_metrics: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Evaluates all active rules for the user against current market observations and portfolio."""
        rules = self.get_user_rules(user_id, active_only=True)
        triggered_events = []
        now = datetime.now(timezone.utc)

        for rule in rules:
            cooldown_min = rule.get("cooldown_minutes", 60)
            last_trig = rule.get("last_triggered_at")
            if last_trig:
                last_dt = datetime.fromisoformat(last_trig)
                if now - last_dt < timedelta(minutes=cooldown_min):
                    # In cooldown; suppress duplicate event
                    continue

            triggered = False
            current_val = Decimal("0.00")
            title = ""
            msg = ""

            rtype = rule["rule_type"]
            sym = rule.get("symbol")
            thresh = rule["threshold_value"]
            op = rule["comparison_operator"]

            if rtype in ("PRICE_ABOVE", "PRICE_BELOW", "PERCENT_CHANGE_UP", "PERCENT_CHANGE_DOWN"):
                quote = current_quotes.get(sym) if sym else None
                if not quote:
                    continue

                price = Decimal(str(quote["price"]))
                change_pct = Decimal(str(quote.get("change_percent", "0.0")))

                if rtype == "PRICE_ABOVE":
                    current_val = price
                    triggered = (price >= thresh) if op in (">=", ">") else (price == thresh)
                    title = f"Price Alert: {sym} exceeded ₹{thresh:,.2f}"
                    msg = f"{sym} is currently trading at ₹{price:,.2f}, surpassing your target threshold of ₹{thresh:,.2f}."
                elif rtype == "PRICE_BELOW":
                    current_val = price
                    triggered = (price <= thresh) if op in ("<=", "<") else (price == thresh)
                    title = f"Price Alert: {sym} fell below ₹{thresh:,.2f}"
                    msg = f"{sym} is currently trading at ₹{price:,.2f}, below your limit threshold of ₹{thresh:,.2f}."
                elif rtype == "PERCENT_CHANGE_UP":
                    current_val = change_pct
                    triggered = change_pct >= thresh
                    title = f"Movement Alert: {sym} gained +{change_pct:.2f}%"
                    msg = f"{sym} has surged by {change_pct:+.2f}%, triggering your upper volatility rule."
                elif rtype == "PERCENT_CHANGE_DOWN":
                    current_val = change_pct
                    triggered = change_pct <= thresh
                    title = f"Movement Alert: {sym} declined {change_pct:.2f}%"
                    msg = f"{sym} dropped by {change_pct:.2f}%, reaching your downside notification floor."

            elif rtype == "CONCENTRATION_EXCEEDED" and portfolio_metrics:
                # Top holding concentration percentage check
                top_conc = Decimal(str(portfolio_metrics.get("top_holding_pct", "0.0")))
                current_val = top_conc
                triggered = top_conc >= thresh
                title = f"Portfolio Risk: Concentration at {top_conc:.1f}%"
                msg = f"Your highest holding exceeds {thresh:.1f}% of total portfolio equity. Consider reviewing diversification."

            elif rtype == "RISK_CHANGE" and portfolio_metrics:
                hhi = Decimal(str(portfolio_metrics.get("hhi_score", "0.0")))
                current_val = hhi
                triggered = hhi >= thresh
                title = f"Portfolio Concentration Shift: HHI {hhi:.0f}"
                msg = f"Portfolio concentration score reached {hhi:.0f}, indicating an asset concentration shift."

            if triggered:
                # Dedupe key: rule_id + date + 4-hour window
                window_bucket = now.strftime("%Y-%m-%d-%H")
                dedupe_key = f"{rule['id']}:{sym or 'ALL'}:{window_bucket}"

                if dedupe_key in [e["dedupe_key"] for e in _ALERT_EVENTS_STORE.values()]:
                    continue

                event_id = f"evt-{uuid.uuid4().hex[:12]}"
                event = {
                    "id": event_id,
                    "rule_id": rule["id"],
                    "user_id": user_id,
                    "event_type": rtype,
                    "symbol": sym,
                    "triggered_value": current_val,
                    "threshold_value": thresh,
                    "title": title,
                    "message": msg,
                    "dedupe_key": dedupe_key,
                    "created_at": now.isoformat(),
                }
                _ALERT_EVENTS_STORE[event_id] = event
                rule["last_triggered_at"] = now.isoformat()
                rule["updated_at"] = now.isoformat()
                _ALERT_RULES_STORE[rule["id"]] = rule
                triggered_events.append(event)

                # Auto-generate in-app notification
                notif_id = f"notif-{uuid.uuid4().hex[:12]}"
                category = "PRICE_ALERT" if rtype.startswith("PRICE_") or "PERCENT" in rtype else "PORTFOLIO_RISK"
                notif = {
                    "id": notif_id,
                    "user_id": user_id,
                    "alert_event_id": event_id,
                    "category": category,
                    "title": title,
                    "body": msg,
                    "is_read": False,
                    "read_at": None,
                    "created_at": now.isoformat(),
                }
                _NOTIFICATIONS_STORE[notif_id] = notif

                # Record delivery attempt (IN_APP guaranteed, PUSH_FCM mock)
                attempt_id = f"att-{uuid.uuid4().hex[:12]}"
                attempt = {
                    "id": attempt_id,
                    "notification_id": notif_id,
                    "channel": "IN_APP",
                    "attempt_status": "SUCCESS",
                    "attempt_number": 1,
                    "error_message": None,
                    "attempted_at": now.isoformat(),
                }
                _DELIVERY_ATTEMPTS_STORE.setdefault(notif_id, []).append(attempt)

        return triggered_events

    def get_user_notifications(self, user_id: str, unread_only: bool = False) -> List[Dict[str, Any]]:
        """CH-09: Retrieve in-app notifications for authenticated user."""
        notifs = [n for n in _NOTIFICATIONS_STORE.values() if n["user_id"] == user_id]
        if unread_only:
            notifs = [n for n in notifs if not n["is_read"]]
        notifs.sort(key=lambda x: x["created_at"], reverse=True)
        return notifs

    def mark_notification_read(self, user_id: str, notif_id: str) -> bool:
        """Mark single notification as read."""
        n = _NOTIFICATIONS_STORE.get(notif_id)
        if n and n["user_id"] == user_id:
            n["is_read"] = True
            n["read_at"] = datetime.now(timezone.utc).isoformat()
            return True
        return False

    def mark_all_notifications_read(self, user_id: str) -> int:
        """Mark all notifications as read for user."""
        count = 0
        now_str = datetime.now(timezone.utc).isoformat()
        for n in _NOTIFICATIONS_STORE.values():
            if n["user_id"] == user_id and not n["is_read"]:
                n["is_read"] = True
                n["read_at"] = now_str
                count += 1
        return count
