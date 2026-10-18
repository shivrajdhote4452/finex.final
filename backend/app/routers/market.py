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

from datetime import datetime, timezone
from typing import List, Optional

from backend.app.adapters.alpaca_paper_adapter import US_INSTRUMENT_REGISTRY, AlpacaPaperAdapter
from backend.app.adapters.market_data_provider import INSTRUMENT_REGISTRY, RealMarketDataProvider
from backend.app.config import get_settings
from backend.app.core.envelope import create_response_envelope
from backend.app.core.errors import NotFoundException
from backend.app.domain.technical_indicators import (
    calculate_bollinger_bands,
    calculate_ema,
    calculate_macd,
    calculate_rsi,
    calculate_sma,
    calculate_vwap,
)
from backend.app.ports.market_data import HistoricalBar, Quote
from fastapi import APIRouter, HTTPException, Query, Request, status

router = APIRouter(prefix="/market", tags=["Market Data"])
settings = get_settings()

provider = RealMarketDataProvider(force_cache=False, allow_fixture_fallback=settings.MARKET_ALLOW_FIXTURES)
alpaca_adapter = AlpacaPaperAdapter(
    api_key=settings.ALPACA_API_KEY,
    secret_key=settings.ALPACA_SECRET_KEY,
    base_url=settings.ALPACA_BASE_URL,
    data_url=settings.ALPACA_DATA_URL,
)


@router.get("/mode")
async def get_market_data_mode(request: Request):
    """Return active data mode, feed coverage label, and SEBI compliance status."""
    cid = getattr(request.state, "correlation_id", None)
    mode = settings.MARKET_DATA_MODE

    feed_label = "NSE Historical Replay"
    if mode == "US_ALPACA_PAPER":
        feed_label = "Live IEX"
    elif mode == "INDIAN_LIVE_DATA":
        feed_label = "NSE / Upstox (Awaiting Regulatory Authorization)"

    return create_response_envelope(
        data={
            "mode": mode,
            "feed_label": feed_label,
            "currency": "USD" if mode == "US_ALPACA_PAPER" else "INR",
            "is_simulated": True,
            "sebi_educational_lag_days": settings.SEBI_EDUCATIONAL_LAG_DAYS,
            "sebi_lag_enforced": mode == "INDIA_HISTORICAL_REPLAY",
            "alpaca_configured": alpaca_adapter.is_configured,
            "current_server_utc": datetime.now(timezone.utc).isoformat(),
        },
        correlation_id=cid,
    )


@router.get("/instruments")
async def list_all_instruments(request: Request, market: Optional[str] = Query(None)):
    """List all supported instruments with sectors, exchange, and canonical IDs."""
    cid = getattr(request.state, "correlation_id", None)
    all_instruments = list(INSTRUMENT_REGISTRY)

    if settings.MARKET_DATA_MODE == "US_ALPACA_PAPER" or market == "US":
        all_instruments.extend(US_INSTRUMENT_REGISTRY)

    if market:
        all_instruments = [
            i
            for i in all_instruments
            if i.get("exchange") == market.upper() or (market.upper() == "US" and i.get("currency") == "USD")
        ]

    return create_response_envelope(
        data={"instruments": all_instruments, "total": len(all_instruments)},
        correlation_id=cid,
    )


@router.get("/search")
async def search_market_instruments(
    request: Request,
    query: str = Query(..., min_length=1, description="Symbol, company name, or sector"),
):
    """Search supported market instruments across NSE and US paper universe."""
    cid = getattr(request.state, "correlation_id", None)
    results = await provider.search_instruments(query)

    # If US instruments match, append
    if settings.MARKET_DATA_MODE == "US_ALPACA_PAPER":
        us_matches = await alpaca_adapter.search_instruments(query)
        results.extend(us_matches)

    return create_response_envelope(
        data={"query": query, "results": results, "count": len(results)},
        correlation_id=cid,
    )


@router.get("/quotes/{symbol}")
async def get_instrument_quote(request: Request, symbol: str):
    """Fetch verified quote for symbol with explicit observation timestamp and freshness status."""
    cid = getattr(request.state, "correlation_id", None)
    clean_sym = symbol.upper()

    # Route US instruments to Alpaca if configured
    quote: Optional[Quote] = None
    if any(inst["symbol"] == clean_sym for inst in US_INSTRUMENT_REGISTRY):
        quote = await alpaca_adapter.get_latest_quote(clean_sym)
    else:
        quote = await provider.get_latest_quote(clean_sym)

    if not quote:
        raise NotFoundException(
            message=f"Instrument '{symbol}' is not supported or quote is currently unavailable. No synthetic price generated."
        )

    return create_response_envelope(data=quote.model_dump(mode="json"), correlation_id=cid)


@router.get("/history/{symbol}")
async def get_instrument_history(
    request: Request,
    symbol: str,
    start_date: str = Query("2025-10-18", description="Start date YYYY-MM-DD"),
    end_date: str = Query("2026-10-18", description="End date YYYY-MM-DD"),
    interval: str = Query("1D", description="Candle interval e.g. 1m, 5m, 15m, 1h, 1D, 1W, 1M"),
    range: Optional[str] = Query(None, description="Preset range: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, max"),
    as_of: Optional[str] = Query(None, description="Simulated replay clock ISO timestamp"),
):
    """Fetch historical price bars, constrained by date range, resolution, and optional as_of replay clock."""
    cid = getattr(request.state, "correlation_id", None)
    clean_sym = symbol.upper()

    as_of_dt: Optional[datetime] = None
    if as_of:
        try:
            as_of_dt = datetime.fromisoformat(as_of.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid as_of timestamp format: '{as_of}'. Expected ISO 8601 string.",
            )

    # Route US instruments to Alpaca adapter if appropriate
    bars: List[HistoricalBar] = []
    if any(inst["symbol"] == clean_sym for inst in US_INSTRUMENT_REGISTRY):
        bars = await alpaca_adapter.get_historical_bars(
            clean_sym, start_date=start_date, end_date=end_date, interval=interval, as_of=as_of_dt
        )
    else:
        bars = await provider.get_historical_bars(
            clean_sym,
            start_date=start_date,
            end_date=end_date,
            interval=interval,
            range_param=range,
            as_of=as_of_dt,
        )

    if not bars:
        raise NotFoundException(
            message=f"No historical price records found for '{symbol}' within date range {start_date} to {end_date}."
        )

    return create_response_envelope(
        data={
            "symbol": clean_sym,
            "interval": interval,
            "range": range,
            "start_date": start_date,
            "end_date": end_date,
            "as_of": as_of_dt.isoformat() if as_of_dt else None,
            "bars": [b.model_dump(mode="json") for b in bars],
            "count": len(bars),
        },
        correlation_id=cid,
    )


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
