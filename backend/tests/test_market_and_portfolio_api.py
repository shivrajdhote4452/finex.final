"""Contract & Integration Tests for Market Data, Watchlist and Portfolio APIs.

Task ID: S3-API-03
Tests endpoints for market search, quotes, history, watchlists CRUD,
holdings validation, deterministic valuation calculations, and error handling.
"""

from decimal import Decimal

import pytest
from backend.app.config import Settings
from backend.app.domain.portfolio import calculate_portfolio_valuation
from backend.app.factory import create_app
from backend.app.routers.auth import create_access_token
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def app():
    settings = Settings(
        ENVIRONMENT="testing",
        SECRET_KEY="test_secret_key_minimum_32_characters_long_for_security",
    )
    return create_app(settings)


@pytest.fixture
def auth_headers():
    token = create_access_token("usr-shivraj-001", "shivraj.dhote@finex.internal", "Shivraj Dhote")
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_market_instruments_list(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/market/instruments")
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["data"]["total"] >= 8
        symbols = [i["symbol"] for i in data["data"]["instruments"]]
        assert "RELIANCE" in symbols
        assert "TCS" in symbols


@pytest.mark.asyncio
async def test_market_search_endpoint(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Search by symbol
        res = await client.get("/api/v1/market/search?query=tcs")
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["count"] >= 1
        assert data["results"][0]["symbol"] == "TCS"

        # Search by sector
        res_sec = await client.get("/api/v1/market/search?query=Banking")
        assert res_sec.status_code == 200
        sec_data = res_sec.json()["data"]
        assert sec_data["count"] >= 2


@pytest.mark.asyncio
async def test_market_quote_success(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/market/quotes/RELIANCE")
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["symbol"] == "RELIANCE.NS"
        assert data["canonical_id"] == "NSE:RELIANCE"
        assert float(data["price"]) == 2500.00
        assert data["currency"] == "INR"
        assert "observed_at" in data
        assert "ingested_at" in data
        assert data["source"] == "nse_official_report"


@pytest.mark.asyncio
async def test_market_quote_unsupported_symbol_404(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/market/quotes/NON_EXISTENT_CO")
        assert res.status_code == 404
        assert res.json()["success"] is False
        assert "not supported" in res.json()["error"]["message"]


@pytest.mark.asyncio
async def test_market_history_endpoint(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/market/history/TCS?start_date=2026-10-01&end_date=2026-10-16")
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["symbol"] == "TCS"
        assert len(data["bars"]) > 0
        bar = data["bars"][-1]
        assert "open" in bar
        assert "close" in bar
        assert "high" in bar
        assert "low" in bar
        assert float(bar["high"]) >= float(bar["low"])


@pytest.mark.asyncio
async def test_watchlists_crud_workflow(app, auth_headers):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Fetch user's watchlists
        res = await client.get("/api/v1/watchlists", headers=auth_headers)
        assert res.status_code == 200
        wls = res.json()["data"]["watchlists"]
        assert len(wls) >= 1
        wl_id = wls[0]["id"]

        # 2. Add an item
        add_res = await client.post(
            f"/api/v1/watchlists/{wl_id}/items",
            json={"symbol": "TATAMOTORS"},
            headers=auth_headers,
        )
        assert add_res.status_code == 200
        assert "TATAMOTORS" in add_res.json()["data"]["items"]

        # 3. Prevent duplicate addition (409 Conflict)
        dup_res = await client.post(
            f"/api/v1/watchlists/{wl_id}/items",
            json={"symbol": "TATAMOTORS"},
            headers=auth_headers,
        )
        assert dup_res.status_code == 409
        assert "already pinned" in dup_res.json()["error"]["message"]

        # 4. Remove item
        del_res = await client.delete(
            f"/api/v1/watchlists/{wl_id}/items/TATAMOTORS",
            headers=auth_headers,
        )
        assert del_res.status_code == 200
        assert "TATAMOTORS" not in del_res.json()["data"]["items"]


@pytest.mark.asyncio
async def test_portfolio_valuation_and_summary(app, auth_headers):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Fetch portfolio
        res = await client.get("/api/v1/portfolios/me", headers=auth_headers)
        assert res.status_code == 200
        portfolio = res.json()["data"]
        portfolio_id = portfolio["id"]
        assert len(portfolio["holdings"]) == 4

        # 2. Get deterministic summary
        sum_res = await client.get(f"/api/v1/portfolios/{portfolio_id}/summary", headers=auth_headers)
        assert sum_res.status_code == 200
        summary = sum_res.json()["data"]
        assert float(summary["total_market_value"]) > 0
        assert float(summary["total_cost_basis"]) > 0
        assert summary["is_fully_valued"] is True
        assert len(summary["sector_allocation"]) > 0

        # 3. Add holding
        add_res = await client.post(
            f"/api/v1/portfolios/{portfolio_id}/holdings",
            json={
                "symbol": "TATAMOTORS",
                "quantity": 10.0,
                "cost_basis_per_share": 900.0,
                "asset_class": "EQUITY",
            },
            headers=auth_headers,
        )
        assert add_res.status_code == 200

        # 4. Remove holding
        h_id = add_res.json()["data"]["holding"]["id"]
        del_res = await client.delete(
            f"/api/v1/portfolios/{portfolio_id}/holdings/{h_id}",
            headers=auth_headers,
        )
        assert del_res.status_code == 200


def test_deterministic_portfolio_calculation_isolated():
    """Isolated unit test verifying calculation logic and partial valuation when quote is missing."""
    holdings = [
        {"symbol": "RELIANCE", "quantity": Decimal("10"), "cost_basis_per_share": Decimal("2300.00")},
        {"symbol": "MISSING_CO", "quantity": Decimal("5"), "cost_basis_per_share": Decimal("100.00")},
    ]
    quotes = {
        "RELIANCE": Decimal("2500.00"),
    }
    sectors = {"RELIANCE": "Energy"}

    res = calculate_portfolio_valuation("test-p-1", holdings, quotes, sectors)

    assert res.is_fully_valued is False
    assert "MISSING_CO" in res.missing_quote_symbols
    assert res.total_market_value == Decimal("25000.00")
    assert res.total_cost_basis == Decimal("23500.00")
    assert res.total_unrealized_pnl == Decimal("2000.00")
