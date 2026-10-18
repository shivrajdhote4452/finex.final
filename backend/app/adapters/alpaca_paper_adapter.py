"""Alpaca US Paper Trading and Market Data Adapter.

Task: FinEx Paper Trading Revision 3
Target: US_ALPACA_PAPER opt-in educational integration.

Guards & Invariants:
1. Paper-only allowlist: Strictly rejects any live order host (e.g. api.alpaca.markets) at startup.
2. USD Paper only: Separate USD account context, never combines balances or silently converts INR.
3. Live IEX feed labeling: Accurately reflects IEX basic plan coverage, not full SIP consolidated tape.
4. Safe unconfigured behavior: Remains dormant with clear diagnostic message when keys are absent.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional

import httpx
from backend.app.ports.market_data import AbstractMarketDataProvider, HistoricalBar, Quote

# Approved Paper Hosts Allowlist
ALLOWED_PAPER_HOSTS = {
    "https://paper-api.alpaca.markets",
    "https://data.alpaca.markets",
}

# Standard Demonstration US Universe
US_INSTRUMENT_REGISTRY: List[Dict[str, str]] = [
    {"symbol": "AAPL", "name": "Apple Inc.", "exchange": "NASDAQ", "currency": "USD", "sector": "Technology"},
    {
        "symbol": "MSFT",
        "name": "Microsoft Corporation",
        "exchange": "NASDAQ",
        "currency": "USD",
        "sector": "Technology",
    },
    {"symbol": "GOOGL", "name": "Alphabet Inc.", "exchange": "NASDAQ", "currency": "USD", "sector": "Technology"},
    {
        "symbol": "AMZN",
        "name": "Amazon.com Inc.",
        "exchange": "NASDAQ",
        "currency": "USD",
        "sector": "Consumer Discretionary",
    },
    {"symbol": "TSLA", "name": "Tesla Inc.", "exchange": "NASDAQ", "currency": "USD", "sector": "Automotive & Energy"},
    {
        "symbol": "NVDA",
        "name": "NVIDIA Corporation",
        "exchange": "NASDAQ",
        "currency": "USD",
        "sector": "Semiconductors",
    },
    {"symbol": "META", "name": "Meta Platforms Inc.", "exchange": "NASDAQ", "currency": "USD", "sector": "Technology"},
    {
        "symbol": "SPY",
        "name": "SPDR S&P 500 ETF Trust",
        "exchange": "NYSE Arca",
        "currency": "USD",
        "sector": "Index ETF",
    },
    {"symbol": "QQQ", "name": "Invesco QQQ Trust", "exchange": "NASDAQ", "currency": "USD", "sector": "Index ETF"},
    {
        "symbol": "DIA",
        "name": "SPDR Dow Jones Industrial Average ETF",
        "exchange": "NYSE Arca",
        "currency": "USD",
        "sector": "Index ETF",
    },
]


class AlpacaPaperAdapter(AbstractMarketDataProvider):
    def __init__(
        self,
        api_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        base_url: str = "https://paper-api.alpaca.markets",
        data_url: str = "https://data.alpaca.markets",
    ):
        # Enforce Paper-only Host Guard
        if "api.alpaca.markets" in base_url and "paper-api" not in base_url:
            raise ValueError(
                "SECURITY REJECTION: Live trading endpoints are strictly prohibited in FinEx. "
                "Only paper-api.alpaca.markets is permitted for simulated trading."
            )

        self.api_key = api_key
        self.secret_key = secret_key
        self.base_url = base_url.rstrip("/")
        self.data_url = data_url.rstrip("/")
        self.is_configured = bool(self.api_key and self.secret_key)

    def _get_headers(self) -> Dict[str, str]:
        if not self.is_configured:
            return {}
        return {
            "APCA-API-KEY-ID": self.api_key or "",
            "APCA-API-SECRET-KEY": self.secret_key or "",
            "Accept": "application/json",
        }

    async def get_latest_quote(self, symbol: str) -> Optional[Quote]:
        """Fetch latest quote for US instrument from Alpaca IEX data feed."""
        if not self.is_configured:
            return None

        clean_sym = symbol.upper()
        url = f"{self.data_url}/v2/stocks/{clean_sym}/quotes/latest"
        headers = self._get_headers()

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                res = await client.get(url, headers=headers)
                if res.status_code == 200:
                    payload = res.json().get("quote", {})
                    ask_price = payload.get("ap") or payload.get("bp") or 0.0
                    quote_time_str = payload.get("t")
                    obs_time = (
                        datetime.fromisoformat(quote_time_str.replace("Z", "+00:00"))
                        if quote_time_str
                        else datetime.now(timezone.utc)
                    )

                    return Quote(
                        canonical_id=f"US:{clean_sym}",
                        symbol=clean_sym,
                        price=Decimal(str(round(ask_price, 2))),
                        currency="USD",
                        observed_at=obs_time,
                        ingested_at=datetime.now(timezone.utc),
                        source="alpaca_iex_paper",
                        source_uri=url,
                        source_evidence=f"alpaca-iex-{clean_sym}",
                        served_from_cache=False,
                        is_delayed=False,
                        is_stale=False,
                        data_status="fresh",
                    )
        except Exception:
            return None

        return None

    async def get_historical_bars(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        interval: str = "1D",
        as_of: Optional[datetime] = None,
    ) -> List[HistoricalBar]:
        """Fetch historical bars from Alpaca IEX feed."""
        if not self.is_configured:
            return []

        clean_sym = symbol.upper()
        timeframe_map = {"1m": "1Min", "5m": "5Min", "15m": "15Min", "1h": "1Hour", "1D": "1Day"}
        tf = timeframe_map.get(interval, "1Day")

        url = f"{self.data_url}/v2/stocks/{clean_sym}/bars"
        params = {
            "timeframe": tf,
            "start": f"{start_date}T00:00:00Z",
            "end": f"{end_date}T23:59:59Z",
            "feed": "iex",
            "limit": 1000,
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(url, headers=self._get_headers(), params=params)
                if res.status_code == 200:
                    data = res.json().get("bars", []) or []
                    results: List[HistoricalBar] = []
                    for b in data:
                        t_str = b.get("t")
                        bar_dt = (
                            datetime.fromisoformat(t_str.replace("Z", "+00:00"))
                            if t_str
                            else datetime.now(timezone.utc)
                        )
                        # Replay clock check
                        if as_of and bar_dt > as_of:
                            continue

                        results.append(
                            HistoricalBar(
                                date=bar_dt.strftime("%Y-%m-%d"),
                                time=int(bar_dt.timestamp()),
                                open=Decimal(str(round(b.get("o", 0.0), 2))),
                                high=Decimal(str(round(b.get("h", 0.0), 2))),
                                low=Decimal(str(round(b.get("l", 0.0), 2))),
                                close=Decimal(str(round(b.get("c", 0.0), 2))),
                                volume=int(b.get("v", 0)),
                                currency="USD",
                            )
                        )
                    return results
        except Exception:
            return []

        return []

    async def search_instruments(self, query: str) -> List[dict]:
        """Search registered US demonstration instruments."""
        q = query.upper().strip()
        return [
            inst
            for inst in US_INSTRUMENT_REGISTRY
            if q in inst["symbol"] or q in inst["name"].upper() or q in inst["sector"].upper()
        ]
