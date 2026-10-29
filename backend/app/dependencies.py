from backend.app.adapters.market_data_provider import RealMarketDataProvider
from backend.app.config import get_settings
from backend.app.database import get_db
from backend.app.ports.market_data import AbstractMarketDataProvider
from backend.app.services.angel_adapter import AngelOneMarketAdapter
from backend.app.services.market_hub import MarketHub, get_market_hub

_angel_adapter_instance = None


def get_angel_adapter() -> AngelOneMarketAdapter:
    """FastAPI Dependency for AngelOneMarketAdapter singleton."""
    global _angel_adapter_instance
    if _angel_adapter_instance is None:
        _angel_adapter_instance = AngelOneMarketAdapter()
    return _angel_adapter_instance


def set_angel_adapter(adapter: AngelOneMarketAdapter) -> None:
    """Set global AngelOneMarketAdapter singleton."""
    global _angel_adapter_instance
    _angel_adapter_instance = adapter


def get_market_data_provider() -> AbstractMarketDataProvider:
    """FastAPI Dependency for active AbstractMarketDataProvider based on MARKET_DATA_MODE."""
    settings = get_settings()
    if getattr(settings, "MARKET_DATA_MODE", "") == "INDIAN_LIVE_DATA":
        angel = get_angel_adapter()
        if angel.is_configured():
            return angel
    return RealMarketDataProvider(
        force_cache=False, allow_fixture_fallback=getattr(settings, "MARKET_ALLOW_FIXTURES", False)
    )


__all__ = [
    "get_db",
    "get_market_hub",
    "get_angel_adapter",
    "set_angel_adapter",
    "get_market_data_provider",
    "MarketHub",
    "AngelOneMarketAdapter",
    "AbstractMarketDataProvider",
]
