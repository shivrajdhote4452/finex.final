from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field


class Quote(BaseModel):
    canonical_id: str = Field(..., description="Canonical instrument symbol e.g., NSE:RELIANCE")
    symbol: str = Field(..., description="Provider symbol e.g., RELIANCE.NS")
    price: Decimal = Field(..., description="Observation close or latest price")
    currency: str = Field("INR", description="ISO currency code")
    observed_at: datetime = Field(..., description="UTC timestamp of market observation")
    ingested_at: datetime = Field(..., description="UTC timestamp when data was ingested")
    source: str = Field(..., description="Data provider name (e.g. yfinance, nse_report)")
    served_from_cache: bool = Field(False, description="Whether returned from cached storage")
    is_delayed: bool = Field(False, description="Whether the quote is delayed")


class HistoricalBar(BaseModel):
    date: str = Field(..., description="YYYY-MM-DD trading date")
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    adj_close: Optional[Decimal] = None
    volume: int
    currency: str = "INR"


class AbstractMarketDataProvider(ABC):
    """Port interface for market data acquisition."""

    @abstractmethod
    async def get_latest_quote(self, symbol: str) -> Optional[Quote]:
        """Fetch latest verified quote for symbol or return None if unavailable."""
        pass

    @abstractmethod
    async def get_historical_bars(self, symbol: str, start_date: str, end_date: str) -> List[HistoricalBar]:
        """Fetch historical daily bars for the specified date range."""
        pass

    @abstractmethod
    async def search_instruments(self, query: str) -> List[dict]:
        """Search instruments matching the query string."""
        pass
