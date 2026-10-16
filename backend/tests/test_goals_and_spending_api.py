"""Integration Tests for Financial Goals and Spending Analytics API.

Task ID: S7-API-01, S7-API-02, S7-API-03, S7-DAT-03, S7-AI-01, S7-AI-02, S7-AI-03
Author: Shivraj Dhote
Date: 16 October 2026
"""

import pytest
from ai.evaluation.evaluate_sprint7 import run_sprint7_evaluations
from backend.app.domain.goal_engine import (
    _CONTRIBUTIONS_STORE,
    _GOALS_STORE,
    _PROJECTIONS_STORE,
)
from backend.app.domain.spending_service import (
    _TRANSACTIONS_STORE,
    _UPLOADS_STORE,
)
from backend.app.factory import create_app
from backend.app.routers.auth import create_access_token
from data.quality.goal_spending_reconciliation import GoalSpendingReconciler
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
def auth_headers():
    token = create_access_token("usr-shivraj-001", "shivraj.dhote@finex.internal", "Shivraj Dhote")
    return {
        "Authorization": f"Bearer {token}",
        "X-Correlation-ID": "corr-sprint7-test-001",
    }


@pytest.fixture
def other_user_headers():
    token = create_access_token("usr-other-002", "other@finex.internal", "Other Investor")
    return {
        "Authorization": f"Bearer {token}",
        "X-Correlation-ID": "corr-sprint7-other-user",
    }


@pytest.fixture(autouse=True)
def clean_stores():
    _GOALS_STORE.clear()
    _CONTRIBUTIONS_STORE.clear()
    _PROJECTIONS_STORE.clear()
    _UPLOADS_STORE.clear()
    _TRANSACTIONS_STORE.clear()
    yield
    _GOALS_STORE.clear()
    _CONTRIBUTIONS_STORE.clear()
    _PROJECTIONS_STORE.clear()
    _UPLOADS_STORE.clear()
    _TRANSACTIONS_STORE.clear()


@pytest.mark.asyncio
async def test_goal_crud_and_projection_lifecycle(app, auth_headers):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Reject past target date
        bad_res = await client.post(
            "/api/v1/goals",
            json={
                "title": "Past Goal",
                "category": "EMERGENCY_FUND",
                "target_amount": 100000.0,
                "current_amount": 10000.0,
                "target_date": "2025-01-01",  # Past date
                "assumed_annual_return_pct": 7.0,
            },
            headers=auth_headers,
        )
        assert bad_res.status_code == 422

        # 2. Create valid goal
        res = await client.post(
            "/api/v1/goals",
            json={
                "title": "Emergency Reserve",
                "category": "EMERGENCY_FUND",
                "target_amount": 300000.0,
                "current_amount": 50000.0,
                "target_date": "2027-10-16",
                "assumed_annual_return_pct": 6.0,
            },
            headers=auth_headers,
        )
        assert res.status_code == 201
        goal = res.json()["data"]
        goal_id = goal["id"]
        assert goal["title"] == "Emergency Reserve"

        # 3. List goals
        list_res = await client.get("/api/v1/goals", headers=auth_headers)
        assert list_res.status_code == 200
        assert list_res.json()["data"]["total"] >= 1

        # 4. Get projection
        proj_res = await client.get(f"/api/v1/goals/{goal_id}/projection", headers=auth_headers)
        assert proj_res.status_code == 200
        proj = proj_res.json()["data"]
        assert proj["target_amount"] == 300000.0
        assert proj["required_monthly_savings"] > 0
        assert "STATUTORY DISCLAIMER" in proj["statutory_disclaimer"]

        # 5. Record contribution
        contrib_res = await client.post(
            f"/api/v1/goals/{goal_id}/contributions",
            json={
                "amount": 20000.0,
                "contribution_date": "2026-10-16",
                "notes": "October monthly transfer",
            },
            headers=auth_headers,
        )
        assert contrib_res.status_code == 200
        assert float(contrib_res.json()["data"]["updated_goal_balance"]) == 70000.0


@pytest.mark.asyncio
async def test_spending_csv_upload_masking_and_summary(app, auth_headers, other_user_headers):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        sample_csv = (
            "Date,Amount,Description,Type\n"
            "2026-10-01,50000.00,SALARY CREDIT FROM ACME CORP,CREDIT\n"
            "2026-10-02,1250.00,UPI/524312984512/SWIGGY BANGALORE,DEBIT\n"
            "2026-10-05,3400.00,BLINKIT 10 MIN GROCERIES INDIRANAGAR,DEBIT\n"
            "2026-10-08,1999.00,AIRTEL FIBER BROADBAND BILLPAY 9876543210,DEBIT\n"
            "2026-10-10,15000.00,ZERODHA BROKING MUTUAL FUND SIP,DEBIT\n"
        )

        # 1. Ingest CSV
        up_res = await client.post(
            "/api/v1/spending/upload",
            json={
                "file_name": "hdfc_statement_oct2026.csv",
                "csv_content": sample_csv,
            },
            headers=auth_headers,
        )
        assert up_res.status_code == 200
        up_data = up_res.json()["data"]
        assert up_data["accepted_count"] == 5
        assert up_data["quarantined_count"] == 0

        # 2. Reject duplicate CSV upload
        dup_res = await client.post(
            "/api/v1/spending/upload",
            json={
                "file_name": "hdfc_statement_oct2026.csv",
                "csv_content": sample_csv,
            },
            headers=auth_headers,
        )
        assert dup_res.status_code == 422

        # 3. List transactions & verify masking
        tx_res = await client.get("/api/v1/spending/transactions", headers=auth_headers)
        assert tx_res.status_code == 200
        txs = tx_res.json()["data"]["transactions"]
        assert len(txs) == 5

        swiggy_tx = next(t for t in txs if "SWIGGY" in t["masked_description"])
        assert "****" in swiggy_tx["masked_description"]
        assert "524312984512" not in swiggy_tx["masked_description"]  # 12-digit number strictly masked
        assert swiggy_tx["category_id"] == "FOOD_DINING"

        # 4. Correct category
        tx_id = swiggy_tx["id"]
        patch_res = await client.patch(
            f"/api/v1/spending/transactions/{tx_id}/category",
            json={"category_id": "OTHER"},
            headers=auth_headers,
        )
        assert patch_res.status_code == 200
        assert patch_res.json()["data"]["category_id"] == "OTHER"
        assert patch_res.json()["data"]["categorization_method"] == "USER_CORRECTED"

        # 5. Monthly summary roll-up
        sum_res = await client.get("/api/v1/spending/summary?year_month=2026-10", headers=auth_headers)
        assert sum_res.status_code == 200
        summary = sum_res.json()["data"]
        assert summary["total_credit"] == 50000.00
        assert summary["total_debit"] == 21649.00
        assert summary["net_savings"] == 28351.00
        assert summary["savings_rate_pct"] == pytest.approx(56.7, 0.1)

        # 6. User Isolation check: other user sees zero transactions
        other_tx_res = await client.get("/api/v1/spending/transactions", headers=other_user_headers)
        assert other_tx_res.status_code == 200
        assert len(other_tx_res.json()["data"]["transactions"]) == 0


def test_goal_and_spending_reconciliation():
    reconciler = GoalSpendingReconciler()
    goals = [
        {
            "id": "g-01",
            "title": "Car Goal",
            "current_amount": "50000.00",
            "target_date": "2028-10-16",
        }
    ]
    contributions = [
        {"id": "c-01", "goal_id": "g-01", "amount": "25000.00"},
        {"id": "c-02", "goal_id": "g-01", "amount": "25000.00"},
    ]
    transactions = [
        {"id": "t-01", "dedupe_hash": "hash-001", "masked_description": "SWIGGY"},
        {"id": "t-02", "dedupe_hash": "hash-002", "masked_description": "BLINKIT"},
    ]
    monthly_summary = {
        "year_month": "2026-10",
        "total_debit": "1000.00",
        "category_breakdown": {
            "FOOD_DINING": "400.00",
            "GROCERIES": "600.00",
        },
    }

    report = reconciler.reconcile(
        goals=goals,
        contributions=contributions,
        transactions=transactions,
        monthly_summary=monthly_summary,
    )

    assert report.is_clean is True
    assert report.goals_reconciled is True
    assert report.spending_reconciled is True
    assert report.breaks_count == 0


def test_sprint7_ai_evaluations_suite():
    rep = run_sprint7_evaluations()
    assert rep["metrics"]["overall_status"] == "PASSED"
    assert rep["metrics"]["goal_numeric_accuracy_pct"] == 100.0
    assert rep["metrics"]["privacy_masking_score_pct"] == 100.0
    assert rep["metrics"]["categorization_accuracy_pct"] == 100.0
