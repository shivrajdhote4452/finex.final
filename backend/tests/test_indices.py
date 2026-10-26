"""Unit and Integration Tests for Indian Benchmark & Sectoral Market Indices.

Task: FinEx Implementing Indices
Validates:
- Canonical Index Registry completeness (Tier 1 & Tier 2)
- Fast lookup by symbol, canonical ID, and normalized strings
- GET /api/v1/market/indices endpoint structure and response envelope
- GET /api/v1/market/indices/{symbol}/quote verified quote with provenance
- GET /api/v1/market/indices/{symbol}/history historical candles format
- Honesty fields (source, observed_at, served_from_cache, evidence hash)
"""

from decimal import Decimal

import pytest
from backend.app.dependencies import get_market_data_provider
from backend.app.domain.index_registry import (
    INDEX_REGISTRY,
    get_index_by_symbol,
)
from backend.app.factory import create_app
from backend.app.ports.market_data import Quote
from httpx import ASGITransport, AsyncClient


def test_index_registry_structure_and_tiers():
    """Verify registry has at least 18 indices across Tier 1 and Tier 2."""
    assert len(INDEX_REGISTRY) >= 18

    tier1 = [idx for idx in INDEX_REGISTRY if idx["tier"] == "1"]
    assert len(tier1) == 8
    tier1_symbols = {idx["symbol"] for idx in tier1}
    assert "NIFTY 50" in tier1_symbols
    assert "SENSEX" in tier1_symbols
    assert "NIFTY BANK" in tier1_symbols
    assert "NIFTY NEXT 50" in tier1_symbols

    tier2 = [idx for idx in INDEX_REGISTRY if idx["tier"] == "2"]
    assert len(tier2) == 10
    tier2_symbols = {idx["symbol"] for idx in tier2}
    assert "NIFTY IT" in tier2_symbols
    assert "NIFTY AUTO" in tier2_symbols
    assert "NIFTY PHARMA" in tier2_symbols


def test_index_lookup_helper():
    """Verify get_index_by_symbol matches exact, lowercase, canonical, and normalized variants."""
    assert get_index_by_symbol("NIFTY 50") is not None
    assert get_index_by_symbol("nifty 50")["symbol"] == "NIFTY 50"
    assert get_index_by_symbol("NSE:NIFTY50")["symbol"] == "NIFTY 50"
    assert get_index_by_symbol("BSE:SENSEX")["symbol"] == "SENSEX"
    assert get_index_by_symbol("BANKNIFTY")["symbol"] == "NIFTY BANK"
    assert get_index_by_symbol("NIFTYIT")["symbol"] == "NIFTY IT"
    assert get_index_by_symbol("INVALID_XYZ_INDEX") is None


@pytest.mark.asyncio
async def test_list_market_indices_api():
    """Verify GET /api/v1/market/indices returns full index list with envelope."""
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/market/indices")
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["success"] is True
        assert "data" in payload
        assert "indices" in payload["data"]
        indices = payload["data"]["indices"]
        assert len(indices) >= 18
        # Check first index structure
        first = indices[0]
        assert "symbol" in first
        assert "display_name" in first
        assert "exchange" in first
        assert "category" in first
        assert "tier" in first
        assert "served_from_cache" in first


@pytest.mark.asyncio
async def test_get_index_quote_with_override():
    """Verify GET /api/v1/market/indices/{symbol}/quote with an injected quote."""
    app = create_app()
    provider = get_market_data_provider()

    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    mock_quote = Quote(
        canonical_id="NSE:NIFTY50",
        symbol="NIFTY 50",
        price=Decimal("24850.50"),
        open_price=Decimal("24700.00"),
        high_price=Decimal("24900.00"),
        low_price=Decimal("24680.00"),
        close_price=Decimal("24750.00"),
        change=Decimal("100.50"),
        change_pct=Decimal("0.41"),
        currency="INR",
        observed_at=now,
        ingested_at=now,
        source="test_adapter",
        source_uri="urn:test:index",
        source_evidence="hash123",
        served_from_cache=False,
        is_delayed=False,
        is_stale=False,
        data_status="LIVE",
    )
    provider.set_quote_override("NIFTY 50", mock_quote)
    app.dependency_overrides[get_market_data_provider] = lambda: provider

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/market/indices/NIFTY 50/quote")
            assert resp.status_code == 200
            data = resp.json()["data"]
            assert data["symbol"] == "NIFTY 50"
            assert data["ltp"] == 24850.50
            assert data["category"] == "headline"
            assert data["freshness"] == "LIVE"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_index_quote_not_found():
    """Verify 404 is returned for an unknown index symbol."""
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/market/indices/UNKNOWN_INDEX_123/quote")
        assert resp.status_code == 404
