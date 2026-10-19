"""Unit and Integration Tests for Angel One SmartAPI Market Data & WebSocket Hub.

Specification: FinEx Real-Time Market Data & Live Charting
Validates:
- AngelOneMarketAdapter implements AbstractMarketDataProvider
- Full 39 Nifty instruments token registry coverage
- AngelOneMarketAdapter initialization & TOTP generation
- async get_latest_quote with Quote schema conformance
- async get_historical_bars with HistoricalBar schema conformance
- async search_instruments with provider_token enrichment
- MarketHub WebSocket connection management & tick broadcast
- /api/v1/market/quotes/{symbol} with LTP & freshness
- /api/v1/market/history/{symbol} historical candles format
- /api/v1/market/ws/{symbol} real-time WebSocket tick streaming
"""

from decimal import Decimal
import json
from unittest.mock import MagicMock, patch

import pytest
from starlette.testclient import TestClient

from backend.app.adapters.market_data_provider import INSTRUMENT_REGISTRY
from backend.app.dependencies import get_angel_adapter, get_market_hub
from backend.app.ports.market_data import AbstractMarketDataProvider, HistoricalBar, Quote
from backend.app.services.angel_adapter import (
    FINEX_INSTRUMENTS,
    TOKEN_TO_SYMBOL,
    AngelOneMarketAdapter,
)
from backend.app.services.market_hub import MarketHub


@pytest.fixture
def client(app):
    return TestClient(app)


def test_angel_adapter_implements_abstract_market_data_provider():
    """Verify AngelOneMarketAdapter strictly conforms to AbstractMarketDataProvider port."""
    adapter = AngelOneMarketAdapter(api_key="test", client_id="test", mpin="1234", totp_secret="JBSWY3DPEHPK3PXP")
    assert isinstance(adapter, AbstractMarketDataProvider)


def test_angel_adapter_symbol_token_registry():
    """Verify primary 5 NSE instruments are mapped correctly."""
    assert "RELIANCE" in FINEX_INSTRUMENTS
    assert "TCS" in FINEX_INSTRUMENTS
    assert "HDFCBANK" in FINEX_INSTRUMENTS
    assert "INFY" in FINEX_INSTRUMENTS
    assert "ICICIBANK" in FINEX_INSTRUMENTS

    assert FINEX_INSTRUMENTS["RELIANCE"] == "2885"
    assert FINEX_INSTRUMENTS["TCS"] == "11536"
    assert FINEX_INSTRUMENTS["HDFCBANK"] == "1333"
    assert FINEX_INSTRUMENTS["INFY"] == "1594"
    assert FINEX_INSTRUMENTS["ICICIBANK"] == "4963"

    assert TOKEN_TO_SYMBOL["2885"] == "RELIANCE"
    assert TOKEN_TO_SYMBOL["11536"] == "TCS"


def test_angel_adapter_full_nifty_universe_tokens():
    """Verify all 39 instruments in INSTRUMENT_REGISTRY have verified tokens in FINEX_INSTRUMENTS."""
    for inst in INSTRUMENT_REGISTRY:
        sym = inst["symbol"]
        assert sym in FINEX_INSTRUMENTS, f"Symbol {sym} missing from Angel One token registry"
        token = FINEX_INSTRUMENTS[sym]
        assert token and len(token) > 0, f"Token for {sym} is empty"
        assert TOKEN_TO_SYMBOL[token] == sym


def test_angel_adapter_unconfigured_graceful_state():
    """Verify unconfigured adapter handles calls safely without throwing unhandled exceptions."""
    adapter = AngelOneMarketAdapter(api_key="", client_id="", mpin="", totp_secret="")
    assert not adapter.is_configured()
    assert not adapter.authenticate()


def test_angel_adapter_totp_authentication():
    """Verify headless TOTP generation and session generation flow."""
    adapter = AngelOneMarketAdapter(
        api_key="test_api_key",
        client_id="SHIV001",
        mpin="1234",
        totp_secret="JBSWY3DPEHPK3PXP",  # Standard base32 test secret
    )
    assert adapter.is_configured()

    # Mock SmartConnect
    mock_smart_connect = MagicMock()
    mock_smart_connect.generateSession.return_value = {
        "status": True,
        "data": {
            "jwtToken": "mock_jwt_token_12345",
            "refreshToken": "mock_refresh_token_67890",
        },
    }
    mock_smart_connect.getfeedToken.return_value = "mock_feed_token_abcde"
    adapter.smart_api = mock_smart_connect

    success = adapter.authenticate()
    assert success is True
    assert adapter.jwt_token == "mock_jwt_token_12345"
    assert adapter.feed_token == "mock_feed_token_abcde"


@pytest.mark.asyncio
async def test_angel_adapter_get_latest_quote_conformance():
    """Verify get_latest_quote maps SmartAPI ltpData response into compliant Quote port model."""
    adapter = AngelOneMarketAdapter(
        api_key="test_api_key",
        client_id="SHIV001",
        mpin="1234",
        totp_secret="JBSWY3DPEHPK3PXP",
    )
    adapter.jwt_token = "valid_token"

    mock_smart_connect = MagicMock()
    mock_smart_connect.ltpData.return_value = {
        "status": True,
        "data": {
            "exchange": "NSE",
            "tradingsymbol": "RELIANCE-EQ",
            "symboltoken": "2885",
            "open": 2500.0,
            "high": 2525.0,
            "low": 2495.0,
            "close": 2510.0,
            "ltp": 2520.0,
        },
    }
    adapter.smart_api = mock_smart_connect

    quote = await adapter.get_latest_quote("RELIANCE")
    assert quote is not None
    assert isinstance(quote, Quote)
    assert quote.canonical_id == "NSE:RELIANCE"
    assert quote.symbol == "RELIANCE.NS"
    assert quote.price == Decimal("2520.0")
    assert quote.open_price == Decimal("2500.0")
    assert quote.high_price == Decimal("2525.0")
    assert quote.low_price == Decimal("2495.0")
    assert quote.close_price == Decimal("2510.0")
    assert quote.source == "angel_smartapi"
    assert quote.data_status == "fresh"
    assert quote.is_stale is False
    assert quote.served_from_cache is False


@pytest.mark.asyncio
async def test_angel_adapter_get_historical_bars_conformance():
    """Verify get_historical_bars wraps get_historical_candles and returns compliant HistoricalBar instances."""
    adapter = AngelOneMarketAdapter(
        api_key="test_api_key",
        client_id="SHIV001",
        mpin="1234",
        totp_secret="JBSWY3DPEHPK3PXP",
    )
    adapter.jwt_token = "valid_token"

    mock_smart_connect = MagicMock()
    mock_smart_connect.getCandleData.return_value = {
        "status": True,
        "data": [
            ["2026-10-15T09:15:00+05:30", 2500.0, 2520.0, 2490.0, 2515.0, 10500],
            ["2026-10-16T09:15:00+05:30", 2515.0, 2530.0, 2510.0, 2525.0, 12000],
        ],
    }
    adapter.smart_api = mock_smart_connect

    bars = await adapter.get_historical_bars("RELIANCE", "2026-10-15", "2026-10-16", interval="1D")
    assert len(bars) == 2
    b1 = bars[0]
    assert isinstance(b1, HistoricalBar)
    assert b1.open == Decimal("2500.0")
    assert b1.high == Decimal("2520.0")
    assert b1.low == Decimal("2490.0")
    assert b1.close == Decimal("2515.0")
    assert b1.volume == 10500
    assert b1.currency == "INR"


@pytest.mark.asyncio
async def test_angel_adapter_search_instruments():
    """Verify search_instruments enriches registry results with provider_token."""
    adapter = AngelOneMarketAdapter()
    results = await adapter.search_instruments("RELIANCE")
    assert len(results) >= 1
    rel = next((r for r in results if r["symbol"] == "RELIANCE"), None)
    assert rel is not None
    assert rel["provider_token"] == "2885"


def test_angel_adapter_historical_candles_parsing():
    """Verify parsing of Angel One getCandleData format into unified candle objects."""
    adapter = AngelOneMarketAdapter(
        api_key="test_api_key",
        client_id="SHIV001",
        mpin="1234",
        totp_secret="JBSWY3DPEHPK3PXP",
    )
    adapter.jwt_token = "valid_token"

    mock_smart_connect = MagicMock()
    # Format: [timestamp_iso, open, high, low, close, volume]
    mock_smart_connect.getCandleData.return_value = {
        "status": True,
        "data": [
            ["2026-10-16T09:15:00+05:30", 2500.0, 2520.0, 2490.0, 2515.0, 10500],
            ["2026-10-16T09:16:00+05:30", 2515.0, 2525.0, 2510.0, 2522.0, 8400],
        ],
    }
    adapter.smart_api = mock_smart_connect

    candles = adapter.get_historical_candles(
        symbol="RELIANCE",
        interval="ONE_MINUTE",
        from_date="2026-10-16 09:15",
        to_date="2026-10-16 15:30",
    )

    assert len(candles) == 2
    first = candles[0]
    assert "time" in first
    assert first["open"] == 2500.0
    assert first["high"] == 2520.0
    assert first["low"] == 2490.0
    assert first["close"] == 2515.0
    assert first["volume"] == 10500


def test_market_quote_rest_endpoint_with_ltp(client):
    """Verify GET /api/v1/market/quotes/{symbol} provides LTP and freshness."""
    res = client.get("/api/v1/market/quotes/RELIANCE")
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["symbol"] in ("RELIANCE", "RELIANCE.NS")
    assert data.get("clean_symbol", "RELIANCE") == "RELIANCE"
    assert "ltp" in data
    assert data["ltp"] > 0
    assert "freshness" in data
    assert "source" in data
    assert "observed_at" in data


def test_market_history_rest_endpoint_candles(client):
    """Verify GET /api/v1/market/history/{symbol} returns candles list with proper schema."""
    res = client.get("/api/v1/market/history/RELIANCE?interval=1D&days=5")
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["symbol"] == "RELIANCE"
    assert "candles" in data
    assert len(data["candles"]) > 0

    candle = data["candles"][0]
    assert "time" in candle
    assert "open" in candle
    assert "high" in candle
    assert "low" in candle
    assert "close" in candle
    assert "volume" in candle


def test_market_websocket_tick_stream(client):
    """Verify /api/v1/market/ws/{symbol} accepts connection and emits initial snapshot."""
    with client.websocket_connect("/api/v1/market/ws/RELIANCE") as ws:
        msg_text = ws.receive_text()
        tick = json.loads(msg_text)
        assert tick["symbol"] == "RELIANCE"
        assert "ltp" in tick
        assert tick["ltp"] > 0
        assert "open" in tick
        assert "high" in tick
        assert "low" in tick
        assert "close" in tick
        assert "volume" in tick
        assert "source" in tick
        assert "freshness" in tick
        assert "CurrentBarUnixTime" in tick


def test_market_websocket_unsupported_symbol_rejection(client):
    """Verify WebSocket closes connection on unsupported instrument."""
    with pytest.raises(Exception):
        with client.websocket_connect("/api/v1/market/ws/INVALID_SYMBOL_123") as ws:
            ws.receive_text()
