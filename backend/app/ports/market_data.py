from abc import ABC, abstractmethod
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field


class Quote(BaseModel):
    canonical_id: str = Field(..., description="Canonical instrument symbol e.g., NSE:RELIANCE")
    symbol: str = Field(..., description="Provider symbol e.g., RELIANCE.NS")
    price: Decimal = Field(..., description="Observation close or latest price")
    open_price: Optional[Decimal] = Field(None, description="Open price")
    high_price: Optional[Decimal] = Field(None, description="High price")
    low_price: Optional[Decimal] = Field(None, description="Low price")
    close_price: Optional[Decimal] = Field(None, description="Close price")
    change: Optional[Decimal] = Field(None, description="Price change")
    change_pct: Optional[Decimal] = Field(None, description="Percentage change")
    currency: str = "INR"
    observed_at: datetime = Field(..., description="UTC timestamp of market observation")
    ingested_at: datetime = Field(..., description="UTC timestamp when data was ingested")
    source: str = Field(..., description="Data provider name (e.g. yfinance, nse_report)")
    source_uri: Optional[str] = Field(None, description="Source URI or reference endpoint")
    source_evidence: Optional[str] = Field(None, description="Cryptographic SHA-256 hash of observation trace")
    served_from_cache: bool = Field(False, description="Whether returned from cached storage")
    is_delayed: bool = Field(False, description="Whether the quote is delayed")
    is_stale: bool = Field(False, description="Whether the quote is stale")
    data_status: str = Field("fresh", description="Freshness status: fresh, delayed, stale, or unavailable")


class HistoricalBar(BaseModel):
    date: str = Field(..., description="YYYY-MM-DD trading date or ISO timestamp string")
    time: Optional[int] = Field(None, description="Unix timestamp in seconds for charting")
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    adj_close: Optional[Decimal] = None
    volume: int
    currency: str = "INR"

    @property
    def observed_at(self) -> datetime:
        if self.time is not None:
            return datetime.fromtimestamp(self.time, tz=timezone.utc)
        try:
            return datetime.fromisoformat(self.date.replace("Z", "+00:00"))
        except Exception:
            return datetime.strptime(self.date[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)


class AbstractMarketDataProvider(ABC):
    """Port interface for market data acquisition."""

    @abstractmethod
    async def get_latest_quote(self, symbol: str) -> Optional[Quote]:
        """Fetch latest verified quote for symbol or return None if unavailable."""
        pass

    @abstractmethod
    async def get_historical_bars(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        interval: str = "1D",
        as_of: Optional[datetime] = None,
    ) -> List[HistoricalBar]:
        """Fetch historical price bars for the specified date range and interval, capped by optional as_of timestamp."""
        pass

    @abstractmethod
    async def search_instruments(self, query: str) -> List[dict]:
        """Search instruments matching the query string."""
        pass
