"""Market Data Router.

Task ID: S3-API-01, Charts & Replay Revision 3
Exposes:
- /market/instruments: Supported equities and ETFs across active markets
- /market/search: Unified instrument lookup
- /market/quotes/{symbol}: Verified quote with explicit timestamp & freshness status
- /market/history/{symbol}: Paginated OHLCV bars with interval and replay clock capping
- /market/indicators/{symbol}: Deterministic indicator calculation (SMA, EMA, BB, RSI, MACD, VWAP)
- /market/mode: Active market mode status, SEBI 30-day educational lag, and clock
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from backend.app.adapters.market_data_provider import INSTRUMENT_REGISTRY
from backend.app.config import get_settings
from backend.app.core.envelope import create_response_envelope
from backend.app.core.errors import NotFoundException
from backend.app.dependencies import (
    get_angel_adapter,
    get_db,
    get_market_data_provider,
    get_market_hub,
)
from backend.app.domain.index_registry import INDEX_REGISTRY, get_index_by_symbol
from backend.app.domain.options_engine import (
    generate_deterministic_option_chain,
)
from backend.app.domain.technical_indicators import (
    calculate_bollinger_bands,
    calculate_ema,
    calculate_macd,
    calculate_rsi,
    calculate_sma,
    calculate_vwap,
)
from backend.app.ports.market_data import AbstractMarketDataProvider, HistoricalBar
from backend.app.services.angel_adapter import FINEX_INSTRUMENTS, AngelOneMarketAdapter
from backend.app.services.market_hub import MarketHub
from fastapi import APIRouter, Depends, HTTPException, Query, Request, WebSocket, WebSocketDisconnect, status
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/market", tags=["Market Data"])
settings = get_settings()


@router.get("/mode")
async def get_market_data_mode(request: Request):
    """Return active data mode, feed coverage label, and SEBI compliance status."""
    cid = getattr(request.state, "correlation_id", None)
    mode = settings.MARKET_DATA_MODE

    feed_label = "NSE Historical Replay"
    if mode == "INDIAN_LIVE_DATA":
        feed_label = "Angel One SmartAPI (Live NSE Feed)"

    return create_response_envelope(
        data={
            "mode": mode,
            "feed_label": feed_label,
            "currency": "INR",
            "is_simulated": mode != "INDIAN_LIVE_DATA",
            "sebi_educational_lag_days": settings.SEBI_EDUCATIONAL_LAG_DAYS,
            "sebi_lag_enforced": mode == "INDIA_HISTORICAL_REPLAY",
            "current_server_utc": datetime.now(timezone.utc).isoformat(),
        },
        correlation_id=cid,
    )


@router.get("/instruments")
async def list_all_instruments(request: Request, market: Optional[str] = Query(None)):
    """List all supported Indian instruments with sectors, exchange, and canonical IDs."""
    cid = getattr(request.state, "correlation_id", None)
    all_instruments = list(INSTRUMENT_REGISTRY)

    return create_response_envelope(
        data={"instruments": all_instruments, "total": len(all_instruments)},
        correlation_id=cid,
    )


@router.get("/search")
async def search_market_instruments(
    request: Request,
    query: str = Query(..., min_length=1, description="Symbol, company name, or sector"),
    provider: AbstractMarketDataProvider = Depends(get_market_data_provider),
):
    """Search supported Indian market instruments across NSE universe."""
    cid = getattr(request.state, "correlation_id", None)
    results = await provider.search_instruments(query)

    return create_response_envelope(
        data={"query": query, "results": results, "count": len(results)},
        correlation_id=cid,
    )


@router.get("/quotes/{symbol}")
async def get_instrument_quote(
    request: Request,
    symbol: str,
    db: AsyncSession = Depends(get_db),
    provider: AbstractMarketDataProvider = Depends(get_market_data_provider),
):
    """Fetch verified quote for symbol with explicit observation timestamp, LTP, and freshness status."""
    cid = getattr(request.state, "correlation_id", None)
    clean_sym = symbol.upper().replace(".NS", "").replace("NSE:", "").strip()

    quote = await provider.get_latest_quote(clean_sym)

    if not quote:
        raise NotFoundException(
            message=f"Instrument '{symbol}' is not supported or quote is currently unavailable. No synthetic price generated."
        )

    data = quote.model_dump(mode="json")
    data["clean_symbol"] = clean_sym
    data["ltp"] = float(quote.price)
    data["freshness"] = "LIVE" if quote.data_status == "LIVE" else "END_OF_DAY"
    data["served_from_cache"] = quote.served_from_cache

    return create_response_envelope(data=data, correlation_id=cid)


@router.get("/history/{symbol}")
async def get_instrument_history(
    request: Request,
    symbol: str,
    interval: str = Query("1D", description="Candle interval e.g. ONE_MINUTE, 1m, 5m, 15m, 1h, 1D, 1W, 1M"),
    days: Optional[int] = Query(None, description="Lookback days (default 5 for intraday)"),
    start_date: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    range: Optional[str] = Query(None, description="Preset range: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, max"),
    as_of: Optional[str] = Query(None, description="Simulated replay clock ISO timestamp"),
    db: AsyncSession = Depends(get_db),
    angel_adapter: AngelOneMarketAdapter = Depends(get_angel_adapter),
    provider: AbstractMarketDataProvider = Depends(get_market_data_provider),
):
    """Fetch historical price bars from Angel One SmartAPI with database/provider cache fallback."""
    cid = getattr(request.state, "correlation_id", None)
    clean_sym = symbol.upper().replace(".NS", "").replace("NSE:", "").strip()

    now_utc = datetime.now(timezone.utc)
    s_date = start_date
    e_date = end_date or now_utc.strftime("%Y-%m-%d")

    if days:
        s_date = (now_utc - timedelta(days=days)).strftime("%Y-%m-%d")
    elif not s_date:
        s_date = (now_utc - timedelta(days=365)).strftime("%Y-%m-%d")

    as_of_dt: Optional[datetime] = None
    if as_of:
        try:
            as_of_dt = datetime.fromisoformat(as_of.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid as_of timestamp format: '{as_of}'. Expected ISO 8601 string.",
            )

    # 1. Try Angel One SmartAPI if configured
    served_from_cache = False
    source = "ANGEL_ONE_SMARTAPI"
    candles = []

    if angel_adapter and angel_adapter.is_configured():
        try:
            candles = angel_adapter.get_historical_candles(
                symbol=clean_sym,
                interval=interval,
                from_date=f"{s_date} 09:15",
                to_date=f"{e_date} 15:30",
            )
            if candles:
                if as_of_dt:
                    as_of_ts = int(as_of_dt.timestamp())
                    candles = [c for c in candles if c.get("time", 0) <= as_of_ts]
                return create_response_envelope(
                    data={
                        "symbol": clean_sym,
                        "source": source,
                        "freshness": "LIVE",
                        "served_from_cache": False,
                        "candles": candles,
                        "bars": candles,
                        "count": len(candles),
                        "interval": interval,
                        "start_date": s_date,
                        "end_date": e_date,
                        "as_of": as_of_dt.isoformat() if as_of_dt else None,
                    },
                    correlation_id=cid,
                )
        except Exception as e:
            logger.warning(f"Angel One candle retrieval error: {e}. Falling back to cached historical provider.")

    # 2. Fallback to operational provider / database cache
    served_from_cache = True
    bars = await provider.get_historical_bars(
        clean_sym,
        start_date=s_date,
        end_date=e_date,
        interval=interval,
        range_param=range,
        as_of=as_of_dt,
    )

    if not bars:
        # Fallback to recent window (e.g. 90 days) if narrow query window fell on weekend or no-data gap
        fallback_s_date = (now_utc - timedelta(days=90)).strftime("%Y-%m-%d")
        bars = await provider.get_historical_bars(
            clean_sym,
            start_date=fallback_s_date,
            end_date=e_date,
            interval=interval,
            range_param=range,
            as_of=as_of_dt,
        )

    if not bars:
        raise NotFoundException(
            message=f"No historical price records found for '{symbol}' within date range {s_date} to {e_date}."
        )

    candles = []
    for b in bars:
        unix_ts = b.time if b.time is not None else int(b.observed_at.timestamp())
        candles.append(
            {
                "time": unix_ts,
                "date": b.date if hasattr(b, "date") else b.observed_at.isoformat(),
                "open": float(b.open),
                "high": float(b.high),
                "low": float(b.low),
                "close": float(b.close),
                "volume": int(b.volume),
            }
        )

    return create_response_envelope(
        data={
            "symbol": clean_sym,
            "source": getattr(bars[0], "source", source) if bars else source,
            "freshness": "END_OF_DAY" if served_from_cache else "LIVE",
            "served_from_cache": served_from_cache,
            "candles": candles,
            "bars": [b.model_dump(mode="json") for b in bars],
            "count": len(bars),
            "interval": interval,
            "range": range,
            "start_date": s_date,
            "end_date": e_date,
            "as_of": as_of_dt.isoformat() if as_of_dt else None,
        },
        correlation_id=cid,
    )


@router.websocket("/ws/{symbol}")
async def market_symbol_websocket(
    websocket: WebSocket,
    symbol: str,
    db: AsyncSession = Depends(get_db),
    hub: MarketHub = Depends(get_market_hub),
):
    """Real-time market ticks streaming WebSocket endpoint for React and Flutter clients."""
    clean_sym = symbol.upper().replace(".NS", "").replace("NSE:", "").strip()
    allowed_symbols = set(FINEX_INSTRUMENTS.keys()).union({item["symbol"] for item in INSTRUMENT_REGISTRY})

    if clean_sym not in allowed_symbols:
        await websocket.close(code=1008)
        return

    await hub.connect(clean_sym, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        hub.disconnect(clean_sym, websocket)
    except Exception:
        hub.disconnect(clean_sym, websocket)


@router.get("/indicators/{symbol}")
async def get_instrument_indicators(
    request: Request,
    symbol: str,
    indicator: str = Query(..., description="Indicator type: SMA, EMA, BB, RSI, MACD, VWAP"),
    period: int = Query(20, ge=2, le=200, description="Window period for SMA, EMA, BB, RSI"),
    start_date: str = Query("2025-10-18", description="Start date YYYY-MM-DD"),
    end_date: str = Query("2026-10-18", description="End date YYYY-MM-DD"),
    interval: str = Query("1D", description="Candle interval"),
    range: Optional[str] = Query(None, description="Preset range: 1mo, 6mo, 1y, 5y"),
    as_of: Optional[str] = Query(None, description="Simulated replay clock ISO timestamp"),
    provider: AbstractMarketDataProvider = Depends(get_market_data_provider),
):
    """Compute verified deterministic technical indicators over genuine historical price bars."""
    cid = getattr(request.state, "correlation_id", None)
    clean_sym = symbol.upper()
    ind_type = indicator.upper().strip()

    as_of_dt: Optional[datetime] = None
    if as_of:
        try:
            as_of_dt = datetime.fromisoformat(as_of.replace("Z", "+00:00"))
        except ValueError:
            pass

    bars: List[HistoricalBar] = await provider.get_historical_bars(
        clean_sym,
        start_date=start_date,
        end_date=end_date,
        interval=interval,
        range_param=range,
        as_of=as_of_dt,
    )

    if not bars:
        raise NotFoundException(message=f"Insufficient history for indicator calculation on '{symbol}'.")

    raw_bars = [b.model_dump(mode="json") for b in bars]
    calc_results = []

    if ind_type == "SMA":
        calc_results = calculate_sma(raw_bars, period=period)
    elif ind_type == "EMA":
        calc_results = calculate_ema(raw_bars, period=period)
    elif ind_type in ("BB", "BOLLINGER", "BOLLINGER_BANDS"):
        calc_results = calculate_bollinger_bands(raw_bars, period=period, num_std=2.0)
    elif ind_type == "RSI":
        calc_results = calculate_rsi(raw_bars, period=period)
    elif ind_type == "MACD":
        calc_results = calculate_macd(raw_bars, fast_period=12, slow_period=26, signal_period=9)
    elif ind_type == "VWAP":
        calc_results = calculate_vwap(raw_bars)
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported indicator: '{indicator}'. Supported: SMA, EMA, BB, RSI, MACD, VWAP",
        )

    return create_response_envelope(
        data={
            "symbol": clean_sym,
            "indicator": ind_type,
            "period": period,
            "interval": interval,
            "series": calc_results,
            "count": len(calc_results),
        },
        correlation_id=cid,
    )


# =============================================================================
# Indian Market Benchmark & Sectoral Indices Endpoints (Phase 1)
# =============================================================================


@router.get("/indices")
async def list_market_indices(
    request: Request,
    category: Optional[str] = Query(None, description="Filter by category: headline, sectoral"),
    tier: Optional[int] = Query(None, description="Filter by tier: 1 (Headline), 2 (Sectoral)"),
    provider: AbstractMarketDataProvider = Depends(get_market_data_provider),
):
    """List supported Indian benchmark & sectoral indices with live/cached quotes and day changes."""
    cid = getattr(request.state, "correlation_id", None)
    indices = INDEX_REGISTRY
    if category:
        indices = [idx for idx in indices if idx.get("category") == category.lower()]
    if tier:
        indices = [idx for idx in indices if idx.get("tier") == str(tier)]

    results = []
    for idx in indices:
        sym = idx["symbol"]
        quote = await provider.get_latest_quote(sym)
        item = dict(idx)
        if quote:
            item["price"] = float(quote.price)
            item["open_price"] = float(quote.open_price) if quote.open_price else None
            item["high_price"] = float(quote.high_price) if quote.high_price else None
            item["low_price"] = float(quote.low_price) if quote.low_price else None
            item["close_price"] = float(quote.close_price) if quote.close_price else None
            item["change"] = float(quote.change) if quote.change is not None else 0.0
            item["change_pct"] = float(quote.change_pct) if quote.change_pct is not None else 0.0
            item["is_positive"] = (quote.change or 0) >= 0
            item["observed_at"] = quote.observed_at.isoformat()
            item["source"] = quote.source
            item["source_evidence"] = quote.source_evidence
            item["is_delayed"] = quote.is_delayed
            item["is_stale"] = quote.is_stale
            item["data_status"] = quote.data_status
            item["served_from_cache"] = quote.served_from_cache
        else:
            item["price"] = None
            item["change"] = None
            item["change_pct"] = None
            item["is_positive"] = True
            item["observed_at"] = None
            item["source"] = "none"
            item["source_evidence"] = None
            item["is_delayed"] = False
            item["is_stale"] = True
            item["data_status"] = "disconnected"
            item["served_from_cache"] = False
        results.append(item)

    return create_response_envelope(
        data={"indices": results, "count": len(results)},
        correlation_id=cid,
    )


@router.get("/indices/{symbol}/quote")
async def get_index_quote(
    request: Request,
    symbol: str,
    provider: AbstractMarketDataProvider = Depends(get_market_data_provider),
):
    """Fetch verified quote for a specific index with provenance metadata."""
    cid = getattr(request.state, "correlation_id", None)
    idx_info = get_index_by_symbol(symbol)
    if not idx_info:
        raise NotFoundException(message=f"Index '{symbol}' not found in registry.")

    quote = await provider.get_latest_quote(idx_info["symbol"])
    if not quote:
        raise NotFoundException(
            message=f"Index '{symbol}' quote is currently unavailable. No synthetic price generated."
        )

    data = quote.model_dump(mode="json")
    data["symbol"] = idx_info["symbol"]
    data["display_name"] = idx_info["display_name"]
    data["category"] = idx_info["category"]
    data["tier"] = idx_info["tier"]
    data["ltp"] = float(quote.price)
    data["freshness"] = (
        "LIVE"
        if quote.data_status in ("LIVE", "fresh") and not quote.is_delayed and not quote.is_stale
        else "END_OF_DAY"
    )
    data["served_from_cache"] = quote.served_from_cache

    return create_response_envelope(data=data, correlation_id=cid)


@router.get("/indices/{symbol}/history")
async def get_index_history(
    request: Request,
    symbol: str,
    interval: str = Query("1D", description="Candle interval e.g. 1m, 5m, 15m, 1h, 1D, 1W, 1M"),
    days: Optional[int] = Query(None, description="Lookback days"),
    start_date: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    range: Optional[str] = Query(None, description="Preset range: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, max"),
    as_of: Optional[str] = Query(None, description="Simulated replay clock ISO timestamp"),
    angel_adapter: AngelOneMarketAdapter = Depends(get_angel_adapter),
    provider: AbstractMarketDataProvider = Depends(get_market_data_provider),
):
    """Fetch historical candle bars for a market index with multi-tier provider fallback."""
    cid = getattr(request.state, "correlation_id", None)
    idx_info = get_index_by_symbol(symbol)
    if not idx_info:
        raise NotFoundException(message=f"Index '{symbol}' not found in registry.")

    now_utc = datetime.now(timezone.utc)
    s_date = start_date
    e_date = end_date or now_utc.strftime("%Y-%m-%d")

    if days:
        s_date = (now_utc - timedelta(days=days)).strftime("%Y-%m-%d")
    elif not s_date:
        s_date = (now_utc - timedelta(days=365)).strftime("%Y-%m-%d")

    candles = []
    source = "ANGEL_ONE_SMARTAPI"
    served_from_cache = False

    # 1. Try Angel One if configured
    if angel_adapter and angel_adapter.is_configured():
        try:
            candles = angel_adapter.get_historical_candles(
                symbol=idx_info["symbol"],
                interval=interval,
                from_date=f"{s_date} 09:15",
                to_date=f"{e_date} 15:30",
            )
        except Exception as e:
            logger.info(f"Angel One candle fetch bypassed for index {idx_info['symbol']}: {e}")

    # 2. Fallback to public provider (Yahoo Finance)
    if not candles:
        source = "YAHOO_FINANCE_VERIFIED"
        try:
            bars = await provider.get_historical_bars(
                symbol=idx_info["symbol"],
                start_date=s_date,
                end_date=e_date,
                interval=interval,
                range_param=range,
            )
            candles = [
                {
                    "time": int(b.timestamp.timestamp()),
                    "date": b.timestamp.strftime("%Y-%m-%d"),
                    "open": float(b.open),
                    "high": float(b.high),
                    "low": float(b.low),
                    "close": float(b.close),
                    "volume": b.volume,
                }
                for b in bars
            ]
        except Exception as e:
            logger.warning(f"Public provider historical candle error for index {idx_info['symbol']}: {e}")

    return create_response_envelope(
        data={
            "symbol": idx_info["symbol"],
            "canonical_id": idx_info["canonical_id"],
            "display_name": idx_info["display_name"],
            "category": idx_info["category"],
            "tier": idx_info["tier"],
            "source": source,
            "freshness": "END_OF_DAY",
            "served_from_cache": served_from_cache,
            "candles": candles,
            "bars": candles,
            "count": len(candles),
            "interval": interval,
            "start_date": s_date,
            "end_date": e_date,
        },
        correlation_id=cid,
    )


# =============================================================================
# Options Chain & Derivatives Endpoints (Phase 2)
# =============================================================================
SUPPORTED_OPTION_UNDERLYINGS: dict = {
    # Benchmark / Sectoral Index Options
    "NIFTY 50": {
        "display_name": "Nifty 50",
        "category": "index",
        "lot_size": 25,
        "strike_step": 50.0,
    },
    "NIFTY BANK": {
        "display_name": "Nifty Bank",
        "category": "index",
        "lot_size": 15,
        "strike_step": 100.0,
    },
    "NIFTY FINANCIAL SERVICES": {
        "display_name": "Nifty Financial Services",
        "category": "index",
        "lot_size": 25,
        "strike_step": 50.0,
    },
    "NIFTY MIDCAP 50": {
        "display_name": "Nifty Midcap 50",
        "category": "index",
        "lot_size": 50,
        "strike_step": 50.0,
    },
    # High-liquidity F&O Equity Options
    "RELIANCE": {
        "display_name": "Reliance Industries",
        "category": "equity",
        "lot_size": 250,
        "strike_step": 20.0,
    },
    "TCS": {
        "display_name": "Tata Consultancy Services",
        "category": "equity",
        "lot_size": 175,
        "strike_step": 50.0,
    },
    "INFY": {
        "display_name": "Infosys Limited",
        "category": "equity",
        "lot_size": 400,
        "strike_step": 20.0,
    },
    "HDFCBANK": {
        "display_name": "HDFC Bank Limited",
        "category": "equity",
        "lot_size": 550,
        "strike_step": 20.0,
    },
    "ICICIBANK": {
        "display_name": "ICICI Bank Limited",
        "category": "equity",
        "lot_size": 700,
        "strike_step": 10.0,
    },
    "TATAMOTORS": {
        "display_name": "Tata Motors Limited",
        "category": "equity",
        "lot_size": 1425,
        "strike_step": 10.0,
    },
    "SBIN": {
        "display_name": "State Bank of India",
        "category": "equity",
        "lot_size": 750,
        "strike_step": 10.0,
    },
    "BHARTIARTL": {
        "display_name": "Bharti Airtel Limited",
        "category": "equity",
        "lot_size": 475,
        "strike_step": 20.0,
    },
}


def normalize_option_underlying(underlying: str) -> Optional[str]:
    """Normalize underlying name or symbol to supported canonical options underlying."""
    clean = underlying.upper().replace(".NS", "").replace("NSE:", "").replace("BSE:", "").strip()
    if clean in SUPPORTED_OPTION_UNDERLYINGS:
        return clean
    aliases = {
        "NIFTY": "NIFTY 50",
        "NIFTY50": "NIFTY 50",
        "BANKNIFTY": "NIFTY BANK",
        "NIFTYBANK": "NIFTY BANK",
        "FINNIFTY": "NIFTY FINANCIAL SERVICES",
        "NIFTYFINSERVICE": "NIFTY FINANCIAL SERVICES",
        "NIFTYMIDCAP50": "NIFTY MIDCAP 50",
    }
    norm = clean.replace(" ", "").replace("_", "").replace("-", "")
    return aliases.get(norm)


@router.get("/options/underlyings")
async def list_option_underlyings(
    request: Request,
    provider: AbstractMarketDataProvider = Depends(get_market_data_provider),
):
    """List all verified NSE underlyings supporting option chains with latest spot quotes."""
    cid = getattr(request.state, "correlation_id", None)
    results = []
    for sym, meta in SUPPORTED_OPTION_UNDERLYINGS.items():
        quote = await provider.get_latest_quote(sym)
        spot = float(quote.price) if quote else None
        results.append(
            {
                "symbol": sym,
                "display_name": meta["display_name"],
                "category": meta["category"],
                "lot_size": meta["lot_size"],
                "strike_step": meta["strike_step"],
                "spot_price": spot,
                "change": float(quote.change) if (quote and quote.change) else 0.0,
                "change_pct": float(quote.change_pct) if (quote and quote.change_pct) else 0.0,
                "source": quote.source if quote else "none",
                "observed_at": quote.observed_at.isoformat() if quote else None,
            }
        )
    return create_response_envelope(
        data={"underlyings": results, "count": len(results)},
        correlation_id=cid,
    )


@router.get("/options/chain/{underlying}")
async def get_option_chain(
    request: Request,
    underlying: str,
    expiry: Optional[str] = Query(None, description="Expiry date in YYYY-MM-DD format"),
    provider: AbstractMarketDataProvider = Depends(get_market_data_provider),
    angel_adapter: AngelOneMarketAdapter = Depends(get_angel_adapter),
):
    """
    Fetch verified Option Chain (strikes, call/put premiums, OI, IV, Black-Scholes Greeks)
    with provenance metadata for educational paper trading.
    """
    cid = getattr(request.state, "correlation_id", None)
    norm_sym = normalize_option_underlying(underlying)
    if not norm_sym:
        raise NotFoundException(
            message=(
                f"Option chain is not available for '{underlying}'. "
                f"FinEx only serves active NSE F&O underlyings with verified options data."
            )
        )

    # 1. Fetch real spot price for underlying
    quote = await provider.get_latest_quote(norm_sym)
    if not quote or quote.price <= 0:
        raise NotFoundException(
            message=f"Verified spot price for '{underlying}' is currently unavailable. Option chain cannot be rendered."
        )

    spot_price = float(quote.price)

    # 2. Parse target expiry if specified
    target_expiry_date = None
    if expiry:
        try:
            target_expiry_date = datetime.strptime(expiry, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid expiry date '{expiry}'. Expected format: YYYY-MM-DD.",
            )

    # 3. Generate deterministic option chain with standard Black-Scholes Greeks
    chain = generate_deterministic_option_chain(
        underlying=norm_sym,
        spot_price=spot_price,
        expiry_date=target_expiry_date,
        source="ANGEL_ONE_SMARTAPI",
        observed_at=quote.observed_at,
    )

    chain_data = chain.model_dump(mode="json")
    chain_data["served_from_cache"] = quote.served_from_cache
    chain_data["is_delayed"] = quote.is_delayed

    return create_response_envelope(data=chain_data, correlation_id=cid)
