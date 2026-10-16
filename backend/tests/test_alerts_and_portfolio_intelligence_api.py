"""Integration Tests for Smart Alerts, Notifications, and Portfolio Intelligence API.

Task ID: S6-API-01, S6-API-02, S6-API-03, S6-AI-01, S6-AI-02, S6-AI-03
Author: Shivraj Dhote
Date: 16 October 2026
"""

from decimal import Decimal
import pytest
from httpx import ASGITransport, AsyncClient

from ai.evaluation.evaluate_sprint6 import run_sprint6_evaluations
from backend.app.domain.alerts_service import (
    _ALERT_EVENTS_STORE,
    _ALERT_RULES_STORE,
    _DELIVERY_ATTEMPTS_STORE,
    _NOTIFICATIONS_STORE,
)
from backend.app.factory import create_app


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
def auth_headers():
    return {
        "Authorization": "Bearer test-dev-token-sub-usr-shivraj-001",
        "X-Correlation-ID": "corr-sprint6-test-001",
    }


@pytest.fixture
def other_user_headers():
    return {
        "Authorization": "Bearer test-dev-token-sub-usr-other-002",
        "X-Correlation-ID": "corr-sprint6-other-user",
    }


@pytest.fixture(autouse=True)
def clean_stores():
    _ALERT_RULES_STORE.clear()
    _ALERT_EVENTS_STORE.clear()
    _NOTIFICATIONS_STORE.clear()
    _DELIVERY_ATTEMPTS_STORE.clear()
    yield
    _ALERT_RULES_STORE.clear()
    _ALERT_EVENTS_STORE.clear()
    _NOTIFICATIONS_STORE.clear()
    _DELIVERY_ATTEMPTS_STORE.clear()


@pytest.mark.asyncio
async def test_alert_rules_crud_and_validation(app, auth_headers):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Reject invalid rule type
        bad_res = await client.post(
            "/api/v1/alerts/rules",
            json={
                "rule_type": "INVALID_RULE_TYPE",
                "symbol": "TCS",
                "comparison_operator": ">=",
                "threshold_value": 3500.0,
                "threshold_unit": "INR",
            },
            headers=auth_headers,
        )
        assert bad_res.status_code == 422

        # 2. Reject PRICE rule without symbol
        bad_price_res = await client.post(
            "/api/v1/alerts/rules",
            json={
                "rule_type": "PRICE_ABOVE",
                "comparison_operator": ">=",
                "threshold_value": 3500.0,
                "threshold_unit": "INR",
            },
            headers=auth_headers,
        )
        assert bad_price_res.status_code == 422

        # 3. Create valid price alert rule
        res = await client.post(
            "/api/v1/alerts/rules",
            json={
                "rule_type": "PRICE_ABOVE",
                "symbol": "RELIANCE",
                "comparison_operator": ">=",
                "threshold_value": 2600.0,
                "threshold_unit": "INR",
                "cooldown_minutes": 60,
            },
            headers=auth_headers,
        )
        assert res.status_code == 201
        rule = res.json()["data"]
        assert rule["symbol"] == "RELIANCE"
        assert rule["is_active"] is True
        rule_id = rule["id"]

        # 4. List rules
        list_res = await client.get("/api/v1/alerts/rules", headers=auth_headers)
        assert list_res.status_code == 200
        assert list_res.json()["data"]["total"] >= 1

        # 5. Patch rule threshold
        patch_res = await client.patch(
            f"/api/v1/alerts/rules/{rule_id}",
            json={"threshold_value": 2650.0},
            headers=auth_headers,
        )
        assert patch_res.status_code == 200
        assert float(patch_res.json()["data"]["threshold_value"]) == 2650.0

        # 6. Deactivate rule
        deact_res = await client.post(
            f"/api/v1/alerts/rules/{rule_id}/deactivate",
            headers=auth_headers,
        )
        assert deact_res.status_code == 200
        assert deact_res.json()["data"]["is_active"] is False

        # 7. Delete rule
        del_res = await client.delete(f"/api/v1/alerts/rules/{rule_id}", headers=auth_headers)
        assert del_res.status_code == 200
        assert del_res.json()["data"]["deleted"] is True


@pytest.mark.asyncio
async def test_alert_evaluation_cooldown_and_notifications(app, auth_headers):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create a rule: TCS PRICE_ABOVE 3000 (TCS is trading at ₹3,500)
        rule_res = await client.post(
            "/api/v1/alerts/rules",
            json={
                "rule_type": "PRICE_ABOVE",
                "symbol": "TCS",
                "comparison_operator": ">=",
                "threshold_value": 3000.0,
                "threshold_unit": "INR",
                "cooldown_minutes": 60,
            },
            headers=auth_headers,
        )
        assert rule_res.status_code == 201

        # Evaluate alerts
        eval_res1 = await client.post("/api/v1/alerts/evaluate", headers=auth_headers)
        assert eval_res1.status_code == 200
        data1 = eval_res1.json()["data"]
        assert data1["events_triggered"] == 1
        assert "TCS" in data1["events"][0]["title"]

        # Immediate re-evaluation must be suppressed by cooldown
        eval_res2 = await client.post("/api/v1/alerts/evaluate", headers=auth_headers)
        assert eval_res2.status_code == 200
        data2 = eval_res2.json()["data"]
        assert data2["events_triggered"] == 0  # Deduplicated / Cooldown suppressed


@pytest.mark.asyncio
async def test_notifications_lifecycle_and_user_isolation(app, auth_headers, other_user_headers):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Trigger an alert to generate an in-app notification
        await client.post(
            "/api/v1/alerts/rules",
            json={
                "rule_type": "PRICE_ABOVE",
                "symbol": "INFY",
                "comparison_operator": ">=",
                "threshold_value": 1400.0,  # INFY is ₹1,450.00
                "threshold_unit": "INR",
                "cooldown_minutes": 60,
            },
            headers=auth_headers,
        )
        await client.post("/api/v1/alerts/evaluate", headers=auth_headers)

        # Check notifications list
        notif_res = await client.get("/api/v1/notifications", headers=auth_headers)
        assert notif_res.status_code == 200
        n_data = notif_res.json()["data"]
        assert n_data["unread_count"] >= 1
        notif_id = n_data["notifications"][0]["id"]

        # Check unread counter endpoint
        count_res = await client.get("/api/v1/notifications/unread-count", headers=auth_headers)
        assert count_res.status_code == 200
        assert count_res.json()["data"]["unread_count"] >= 1

        # Check delivery audit
        deliv_res = await client.get(f"/api/v1/notifications/{notif_id}/delivery", headers=auth_headers)
        assert deliv_res.status_code == 200
        attempts = deliv_res.json()["data"]["attempts"]
        assert len(attempts) >= 1
        assert attempts[0]["channel"] == "IN_APP"
        assert attempts[0]["attempt_status"] == "SUCCESS"

        # User isolation check: Other user cannot mark or view this notification
        other_res = await client.patch(
            f"/api/v1/notifications/{notif_id}/read",
            headers=other_user_headers,
        )
        assert other_res.status_code == 404

        # Owner marks read
        read_res = await client.patch(
            f"/api/v1/notifications/{notif_id}/read",
            headers=auth_headers,
        )
        assert read_res.status_code == 200
        assert read_res.json()["data"]["is_read"] is True

        # Mark all read
        all_read_res = await client.post("/api/v1/notifications/mark-all-read", headers=auth_headers)
        assert all_read_res.status_code == 200


@pytest.mark.asyncio
async def test_deterministic_portfolio_intelligence(app, auth_headers):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/portfolio-intelligence", headers=auth_headers)
        assert res.status_code == 200
        report = res.json()["data"]

        assert report["total_portfolio_value"] > 0
        assert report["equity_market_value"] > 0
        assert report["cash_balance"] > 0
        assert report["cash_weight_pct"] + report["equity_weight_pct"] == pytest.approx(100.0, 0.1)

        # Concentration & HHI
        assert "hhi_concentration_score" in report
        assert "diversification_score" in report
        assert 1.0 <= report["diversification_score"] <= 10.0

        # Sector Exposures
        assert len(report["sector_exposures"]) >= 1
        assert any("Technology" in s["sector"] or "Financial" in s["sector"] for s in report["sector_exposures"])

        # 15% IT shock stress test
        scenario = report["scenario_shock_15pct_it"]
        assert scenario is not None
        assert scenario["is_hypothetical"] is True
        assert scenario["shock_pct"] == -15.0
        assert scenario["estimated_rupee_impact"] < 0
        assert scenario["post_shock_portfolio_value"] == pytest.approx(
            report["total_portfolio_value"] + scenario["estimated_rupee_impact"], 0.05
        )
        assert "STATUTORY DISCLAIMER" in report["statutory_disclaimer"]


@pytest.mark.asyncio
async def test_custom_scenario_stress_test(app, auth_headers):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/portfolio-intelligence/scenario",
            json={
                "target_sector": "Energy & Petrochemicals",
                "shock_percentage": -15.0,
            },
            headers=auth_headers,
        )
        assert res.status_code == 200
        data = res.json()["data"]
        sc = data["scenario"]
        assert sc["target_sector"] == "Energy & Petrochemicals"
        assert sc["is_hypothetical"] is True
        assert "HYPOTHETICAL" in sc["disclaimer"]


def test_sprint6_ai_evaluation_suite_100_percent():
    report = run_sprint6_evaluations()
    assert report["metrics"]["overall_status"] == "PASSED"
    assert report["metrics"]["intent_routing_accuracy"] == 100.0
    assert report["metrics"]["scenario_numeric_consistency_passed"] is True
    assert report["metrics"]["disclaimer_and_framing_passed"] is True
    assert report["metrics"]["ai_explanation_grounding_passed"] is True
    assert report["metrics"]["missing_data_guardrail_passed"] is True
