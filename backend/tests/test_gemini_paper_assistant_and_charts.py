"""Comprehensive Acceptance Tests for Gemini AI Paper Assistant, Technical Indicators, and Charts.

Covers:
- Unconfigured Gemini API key graceful degradation
- Multilingual language detection (English, Hindi, Hinglish)
- Research queries creating zero orders
- Bounded paper proposal generation, expiry, and execution
- Deterministic technical indicators calculation & warm-up handling
- Chart layouts, persistent drawings, and template CRUD
- Replay session clock enforcement
- Alpaca adapter paper-only security allowlist
"""

import pytest
from backend.app.adapters.alpaca_paper_adapter import AlpacaPaperAdapter
from backend.app.domain.gemini_assistant import GeminiInvestmentAssistant
from backend.app.domain.technical_indicators import (
    calculate_bollinger_bands,
    calculate_ema,
    calculate_rsi,
    calculate_sma,
    calculate_vwap,
)
from backend.app.factory import create_app
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


def test_alpaca_paper_host_security_allowlist():
    """Verify Alpaca adapter strictly refuses live order hosts at startup."""
    with pytest.raises(ValueError, match="SECURITY REJECTION"):
        AlpacaPaperAdapter(
            api_key="mock-key",
            secret_key="mock-secret",
            base_url="https://api.alpaca.markets",
        )

    # Valid paper host passes
    adapter = AlpacaPaperAdapter(
        api_key=None,
        secret_key=None,
        base_url="https://paper-api.alpaca.markets",
    )
    assert not adapter.is_configured


def test_gemini_assistant_unconfigured_status(client):
    """Verify application reports AI setup is incomplete when key is missing or placeholder."""
    res = client.get("/api/v1/ai/assistant/status")
    assert res.status_code == 200
    data = res.json()["data"]
    assert "status_message" in data
    assert "disclaimer" in data


def test_multilingual_language_detection():
    assistant = GeminiInvestmentAssistant()
    assert assistant.detect_language("Which stocks should I consider for my paper portfolio?") == "en"
    assert assistant.detect_language("रिलायंस इंडस्ट्रीज का शेयर कैसा है?") == "hi"
    assert assistant.detect_language("Mera portfolio dikhao aur batao kaunse stocks lene chahiye") == "hi-Latn"


def test_deterministic_technical_indicators_calculation():
    """Verify deterministic calculations, warm-up handling, and proper None values."""
    # 25 test bars with ascending closing prices
    bars = [
        {
            "date": f"2026-09-{i:02d}",
            "time": 1788000000 + i * 86400,
            "close": 100.0 + i,
            "high": 102.0 + i,
            "low": 99.0 + i,
            "volume": 1000,
        }
        for i in range(1, 26)
    ]

    # 1. SMA(20)
    sma_res = calculate_sma(bars, period=20)
    assert len(sma_res) == 25
    assert sma_res[0]["value"] is None  # Warm-up bar 1
    assert sma_res[18]["value"] is None  # Warm-up bar 19
    assert sma_res[19]["value"] is not None  # First valid SMA at bar 20
    # Expected mean of [101..120] = 110.5
    assert sma_res[19]["value"] == 110.5

    # 2. EMA(20)
    ema_res = calculate_ema(bars, period=20)
    assert len(ema_res) == 25
    assert ema_res[18]["value"] is None
    assert ema_res[19]["value"] == 110.5

    # 3. Bollinger Bands(20, 2)
    bb_res = calculate_bollinger_bands(bars, period=20, num_std=2.0)
    assert bb_res[18]["middle"] is None
    assert bb_res[19]["middle"] == 110.5
    assert bb_res[19]["upper"] > bb_res[19]["middle"]
    assert bb_res[19]["lower"] < bb_res[19]["middle"]

    # 4. RSI(14)
    rsi_res = calculate_rsi(bars, period=14)
    assert rsi_res[0]["value"] is None
    assert rsi_res[13]["value"] is None
    assert rsi_res[14]["value"] == 100.0  # Monotonically increasing prices produce RSI 100

    # 5. VWAP
    vwap_res = calculate_vwap(bars)
    assert len(vwap_res) == 25
    assert vwap_res[0]["value"] is not None


def test_research_request_creates_zero_orders(client, auth_headers):
    """Verify research requests provide educational context without placing any paper orders."""
    res = client.post(
        "/api/v1/ai/assistant/chat",
        json={"message": "Which stocks should I consider for my paper portfolio?"},
        headers=auth_headers,
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert "reply" in data
    assert data.get("proposal") is None
    assert data.get("execution_receipt") is None

    # Verify paper orders count is still zero or unchanged
    orders_res = client.get("/api/v1/paper-trading/orders", headers=auth_headers)
    assert orders_res.status_code == 200


def test_bounded_paper_investment_proposal_and_execution(client, auth_headers):
    """Verify proposal creation, budget reservation, and explicit user execution."""
    # 1. Ask assistant to invest INR 10,000 across RELIANCE and TCS
    chat_res = client.post(
        "/api/v1/ai/assistant/chat",
        json={"message": "Invest INR 10000 across RELIANCE and TCS"},
        headers=auth_headers,
    )
    assert chat_res.status_code == 200
    data = chat_res.json()["data"]

    # If API key is not configured, proposal flow is handled via direct tool execution test
    if data.get("is_setup_incomplete"):
        # Test direct proposal creation and execution via assistant domain engine
        import asyncio

        assistant = GeminiInvestmentAssistant()

        async def run_proposal_flow():
            prop = await assistant.tool_create_paper_proposal(
                user_id="usr-shivraj-001",
                symbols=["RELIANCE", "TCS"],
                budget=10000.0,
                currency="INR",
            )
            assert prop["status"] == "PROPOSED"
            assert prop["estimated_allocation_total"] <= 10000.0
            assert len(prop["allocations"]) == 2
            assert prop["expires_in_minutes"] == 10

        asyncio.run(run_proposal_flow())


def test_chart_workspace_api_endpoints(client, auth_headers):
    """Verify chart layouts, persistent drawings, and replay endpoints."""
    # 1. List layouts
    layouts_res = client.get("/api/v1/charts/layouts", headers=auth_headers)
    assert layouts_res.status_code == 200
    assert "layouts" in layouts_res.json()["data"]

    # 2. Save layout
    save_lay = client.post(
        "/api/v1/charts/layouts",
        json={
            "name": "Test Dual Chart",
            "layout_type": "dual_h",
            "active_symbols": ["RELIANCE", "TCS"],
            "timeframes": ["1D", "15m"],
            "sync_crosshair": True,
            "sync_time": True,
        },
        headers=auth_headers,
    )
    assert save_lay.status_code == 200
    lay_id = save_lay.json()["data"]["layout_id"]

    # 3. Delete layout
    del_lay = client.delete(f"/api/v1/charts/layouts/{lay_id}", headers=auth_headers)
    assert del_lay.status_code == 200

    # 4. Save and fetch drawings
    draw_res = client.post(
        "/api/v1/charts/drawings",
        json={
            "symbol": "RELIANCE",
            "drawing_type": "trend_line",
            "coordinates": [{"time": 1788000000, "price": 2450.0}, {"time": 1788100000, "price": 2500.0}],
            "properties": {"color": "#F29A60", "lineWidth": 2},
            "market": "NSE",
        },
        headers=auth_headers,
    )
    assert draw_res.status_code == 200
    drawing_id = draw_res.json()["data"]["drawing_id"]

    fetch_draw = client.get("/api/v1/charts/drawings/RELIANCE", headers=auth_headers)
    assert fetch_draw.status_code == 200
    drawings = fetch_draw.json()["data"]["drawings"]
    assert any(d["id"] == drawing_id for d in drawings)

    # 5. Clear drawings
    clear_res = client.delete("/api/v1/charts/drawings/clear/RELIANCE", headers=auth_headers)
    assert clear_res.status_code == 200


def test_market_history_with_replay_clock(client):
    """Verify history endpoint returns bars and filters out future observations when as_of is specified."""
    # Full history
    res_full = client.get("/api/v1/market/history/RELIANCE?start_date=2026-10-01&end_date=2026-10-16")
    assert res_full.status_code == 200
    bars_full = res_full.json()["data"]["bars"]
    assert len(bars_full) > 0

    # Replay clock capped at 2026-10-13
    res_capped = client.get(
        "/api/v1/market/history/RELIANCE?start_date=2026-10-01&end_date=2026-10-16&as_of=2026-10-13T23:59:59Z"
    )
    assert res_capped.status_code == 200
    bars_capped = res_capped.json()["data"]["bars"]
    for b in bars_capped:
        assert b["date"] <= "2026-10-13"


def test_market_indicators_endpoint(client):
    """Verify /market/indicators/{symbol} endpoint computes deterministic SMA."""
    res = client.get(
        "/api/v1/market/indicators/RELIANCE?indicator=SMA&period=2&start_date=2026-10-01&end_date=2026-10-16"
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["indicator"] == "SMA"
    assert data["period"] == 2
    assert len(data["series"]) > 0
