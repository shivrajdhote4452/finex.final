"""Market Data Router.

Task ID: S3-API-01
Exposes /market/search, /market/quotes/{symbol}, and /market/history/{symbol}
with canonical IDs, freshness metadata, caching indicators, and strict error mapping.
"""

from typing import List, Optional

from backend.app.adapters.market_data_provider import INSTRUMENT_REGISTRY, RealMarketDataProvider
from backend.app.config import get_settings
from backend.app.core.envelope import create_response_envelope
from backend.app.core.errors import NotFoundException
from backend.app.ports.market_data import HistoricalBar, Quote
from fastapi import APIRouter, Query, Request

router = APIRouter(prefix="/market", tags=["Market Data"])
settings = get_settings()
provider = RealMarketDataProvider(force_cache=False, allow_fixture_fallback=settings.MARKET_ALLOW_FIXTURES)


@router.get("/instruments")
async def list_all_instruments(request: Request):
    """List all supported instruments with sectors, exchange, and canonical IDs."""
    cid = getattr(request.state, "correlation_id", None)
    return create_response_envelope(
        data={"instruments": INSTRUMENT_REGISTRY, "total": len(INSTRUMENT_REGISTRY)},
        correlation_id=cid,
    )


@router.get("/search")
async def search_market_instruments(
    request: Request,
    query: str = Query(..., min_length=1, description="Symbol, company name, or sector"),
):
    """Search supported market instruments."""
    cid = getattr(request.state, "correlation_id", None)
    results = await provider.search_instruments(query)
    return create_response_envelope(
        data={"query": query, "results": results, "count": len(results)},
        correlation_id=cid,
    )


@router.get("/quotes/{symbol}")
async def get_instrument_quote(request: Request, symbol: str):
    """Fetch verified quote for symbol with explicit observation timestamp and freshness status."""
    cid = getattr(request.state, "correlation_id", None)
    quote: Optional[Quote] = await provider.get_latest_quote(symbol)

    if not quote:
        raise NotFoundException(
            message=f"Instrument '{symbol}' is not supported or quote is currently unavailable. No synthetic price generated."
        )

    return create_response_envelope(data=quote.model_dump(mode="json"), correlation_id=cid)


@router.get("/history/{symbol}")
async def get_instrument_history(
    request: Request,
    symbol: str,
    start_date: str = Query("2026-10-01", description="Start date YYYY-MM-DD"),
    end_date: str = Query("2026-10-16", description="End date YYYY-MM-DD"),
):
    """Fetch daily OHLCV historical price bars."""
    cid = getattr(request.state, "correlation_id", None)
    bars: List[HistoricalBar] = await provider.get_historical_bars(symbol, start_date, end_date)

    if not bars:
        raise NotFoundException(
            message=f"No historical price records found for '{symbol}' within date range {start_date} to {end_date}."
        )

    return create_response_envelope(
        data={
            "symbol": symbol.upper(),
            "start_date": start_date,
            "end_date": end_date,
            "bars": [b.model_dump(mode="json") for b in bars],
            "count": len(bars),
        },
        correlation_id=cid,
    )
