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

from backend.app.adapters.market_data_provider import INSTRUMENT_REGISTRY, RealMarketDataProvider
from backend.app.config import get_settings
from backend.app.core.envelope import create_response_envelope
from backend.app.core.errors import NotFoundException
from backend.app.dependencies import (
    get_angel_adapter,
    get_db,
    get_market_data_provider,
    get_market_hub,
)
from backend.app.domain.technical_indicators import (
    calculate_bollinger_bands,
    calculate_ema,
    calculate_macd,
    calculate_rsi,
    calculate_sma,
    calculate_vwap,
)
from backend.app.ports.market_data import AbstractMarketDataProvider, HistoricalBar, Quote
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
