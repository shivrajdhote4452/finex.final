"""Dependency injection providers for FastAPI routes."""

from backend.app.database import get_db
from backend.app.services.angel_adapter import AngelOneMarketAdapter
from backend.app.services.market_hub import MarketHub, get_market_hub

_angel_adapter_instance = None


def get_angel_adapter() -> AngelOneMarketAdapter:
    """FastAPI Dependency for AngelOneMarketAdapter singleton."""
    global _angel_adapter_instance
    if _angel_adapter_instance is None:
        _angel_adapter_instance = AngelOneMarketAdapter()
    return _angel_adapter_instance


__all__ = ["get_db", "get_market_hub", "get_angel_adapter", "MarketHub", "AngelOneMarketAdapter"]
