"""Integration and Contract Tests for Sprint 3 AI Modules.

Task ID: S3-AI-01, S3-AI-02, S3-AI-03
Tests:
- /api/v1/ai/compare with authentic Indian equities
- Zero-hallucination missing metrics (Expense Ratio -> not available)
- /api/v1/ai/portfolios/{id}/explain deterministic concentration & diversification
- Unlisted security 404 handling
- Factuality & Evaluation suite 100% pass verification
"""

import os
import pytest
from httpx import ASGITransport, AsyncClient

from ai.evaluation.evaluate_sprint3 import run_sprint3_ai_evaluation
from backend.app.config import Settings
from backend.app.factory import create_app


@pytest.fixture
def app():
    settings = Settings(
        ENVIRONMENT="testing",
        SECRET_KEY="test_secret_key_minimum_32_characters_long_for_security",
    )
    return create_app(settings)


@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer mock-valid-token-user-123"}


@pytest.mark.asyncio
async def test_ai_compare_supported_securities(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/ai/compare?symbol_a=RELIANCE&symbol_b=TCS")
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        cmp_data = data["data"]

        assert cmp_data["entity_a"] == "RELIANCE"
        assert cmp_data["entity_b"] == "TCS"
        assert len(cmp_data["summary_matrix"]) >= 6

        # Check closing prices and sources
        price_row = next(m for m in cmp_data["summary_matrix"] if m["metric"] == "Closing Price")
        assert "₹2,500.00" in price_row["entity_a_value"]
        assert "₹3,500.00" in price_row["entity_b_value"]
        assert "NSE Official Market Feed" in price_row["entity_a_source"]

        # Check zero-hallucination of equity expense ratio
        exp_row = next(m for m in cmp_data["summary_matrix"] if "Expense Ratio" in m["metric"])
        assert exp_row["entity_a_value"] == "not available"
        assert exp_row["entity_b_value"] == "not available"

        # Check statutory educational disclaimer
        assert "EDUCATIONAL DISCLAIMER" in cmp_data["legal_disclaimer"]


@pytest.mark.asyncio
async def test_ai_compare_unsupported_security_404(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/ai/compare?symbol_a=RELIANCE&symbol_b=NON_EXISTENT_CO")
        assert res.status_code == 404
        data = res.json()
        assert data["success"] is False
        assert "not found in verified market data registry" in data["error"]["message"]


@pytest.mark.asyncio
async def test_ai_portfolio_explainer_endpoint(app, auth_headers):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # First ensure default portfolio is available
        p_res = await client.get("/api/v1/portfolios/me", headers=auth_headers)
        assert p_res.status_code == 200
        portfolio_id = p_res.json()["data"]["id"]

        # Request deterministic explanation
        exp_res = await client.get(
            f"/api/v1/ai/portfolios/{portfolio_id}/explain", headers=auth_headers
        )
        assert exp_res.status_code == 200
        data = exp_res.json()["data"]

        assert data["portfolio_id"] == portfolio_id
        assert data["is_fully_valued"] is True
        assert "₹" in data["formatted_total_value"]
        assert len(data["sector_breakdown"]) >= 3
        assert data["concentration_metrics"]["concentration_level"] in [
            "Well Diversified",
            "Moderately Concentrated",
            "Highly Concentrated",
        ]
        assert "EDUCATIONAL DISCLAIMER" in data["disclaimer"]


def test_sprint3_ai_evaluation_suite_100_percent():
    """Verify that all 20 benchmark test cases pass 100% on citations, numbers, freshness, and defense."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_path = os.path.join(base_dir, "..", "ai", "evaluation", "data", "sprint3_ai_evaluation_cases.json")
    report_path = os.path.join(base_dir, "..", "ai", "evaluation", "reports", "sprint3_evaluation_report.json")

    report = run_sprint3_ai_evaluation(data_path, report_path)
    assert report["total_test_cases"] == 20
    assert report["overall_passed_cases"] == 20
    assert report["pass_rate_pct"] == 100.0
    assert report["scores"]["citation_compliance_score"] == 100.0
    assert report["scores"]["numeric_consistency_score"] == 100.0
    assert report["scores"]["freshness_disclosure_score"] == 100.0
    assert report["scores"]["prohibited_claim_defense_score"] == 100.0
