"""FinEx Real-Time Market WebSocket Hub.

Coordinates:
- WebSocket connection management per symbol
- Real-time tick broadcast to connected React & Flutter clients
- Database quote cache integration
- Seamless offline simulated tick streamer when Angel One is unconfigured or market is closed
"""

import asyncio
import json
import logging
import random
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Optional, Set

from backend.app.adapters.market_data_provider import RealMarketDataProvider
from backend.app.services.angel_adapter import FINEX_INSTRUMENTS, TOKEN_TO_SYMBOL
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class MarketHub:
    """Central WebSocket broadcaster for real-time market ticks."""

    def __init__(
        self,
        provider: Optional[RealMarketDataProvider] = None,
        enable_demo_simulation: Optional[bool] = None,
    ):
        from backend.app.config import get_settings

        settings = get_settings()
        self.connections: Dict[str, Set[WebSocket]] = {}
        self.latest_quotes: Dict[str, Dict[str, Any]] = {}
        self.allow_fixtures = getattr(settings, "MARKET_ALLOW_FIXTURES", False)
        self.enable_demo_simulation = (
            enable_demo_simulation
            if enable_demo_simulation is not None
            else getattr(settings, "ENABLE_DEMO_SIMULATION", False)
        )
        if provider:
            self.provider = provider
        elif getattr(settings, "MARKET_DATA_MODE", "") == "INDIAN_LIVE_DATA":
            from backend.app.services.angel_adapter import AngelOneMarketAdapter

            angel = AngelOneMarketAdapter()
            if angel.is_configured():
                self.provider = angel
            else:
                self.provider = RealMarketDataProvider(
                    force_cache=False, allow_fixture_fallback=self.allow_fixtures
                )
        else:
            self.provider = RealMarketDataProvider(
                force_cache=False, allow_fixture_fallback=self.allow_fixtures
            )
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._simulation_task: Optional[asyncio.Task] = None
        self._is_running = False

    def start_angel_stream(self, angel_adapter: Any, loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
        """Connect Angel One live websocket stream to this hub."""
        if loop is not None:
            self._loop = loop
        else:
            try:
                self._loop = asyncio.get_running_loop()
            except RuntimeError:
                try:
                    self._loop = asyncio.get_event_loop()
                except RuntimeError:
                    self._loop = None
        self.provider = angel_adapter
        angel_adapter.start_live_stream(self.handle_angel_raw_tick, auto_reconnect=True)
        logger.info("Angel One live stream connected to MarketHub.")

    def handle_angel_raw_tick(self, raw_message: Any) -> None:
        """Process incoming raw WebSocket message from Angel One SmartWebSocketV2."""
        try:
            # Handle dictionary message from Angel One SDK
            if isinstance(raw_message, dict):
                token = str(raw_message.get("token", raw_message.get("symboltoken", "")))
                symbol = TOKEN_TO_SYMBOL.get(token)
                if not symbol:
                    return

                ltp_raw = raw_message.get("last_traded_price", raw_message.get("ltp", 0.0))
                # SmartAPI prices may be multiplied by 100 in binary feeds
                ltp = float(ltp_raw) / 100.0 if float(ltp_raw) > 100000 else float(ltp_raw)
                now_utc = datetime.now(timezone.utc)

                obs_time_str = raw_message.get("exchange_timestamp") or raw_message.get("observed_at")
                if obs_time_str:
                    try:
                        obs_dt = datetime.fromisoformat(obs_time_str).replace(tzinfo=timezone.utc)
                    except Exception:
                        obs_dt = now_utc
                else:
                    obs_dt = now_utc

                tick = {
                    "symbol": symbol,
                    "status": "AVAILABLE",
                    "ltp": round(ltp, 2),
                    "open": round(float(raw_message.get("open", ltp)), 2),
                    "high": round(float(raw_message.get("high", ltp)), 2),
                    "low": round(float(raw_message.get("low", ltp)), 2),
                    "close": round(ltp, 2),
                    "volume": int(raw_message.get("volume", 0)),
                    "source": "angel_smartapi",
                    "freshness": "LIVE",
                    "data_status": "fresh",
                    "served_from_cache": False,
                    "CurrentBarUnixTime": int(obs_dt.timestamp()),
                    "observed_at": obs_dt.isoformat(),
                    "ingested_at": now_utc.isoformat(),
                }
                self.latest_quotes[symbol] = tick
                # Dispatch tick to subscribers thread-safely
                if self._loop and self._loop.is_running():
                    asyncio.run_coroutine_threadsafe(self.broadcast_tick(symbol, tick), self._loop)
        except Exception as e:
            logger.debug(f"Tick processing notice: {e}")

    async def connect(self, symbol: str, websocket: WebSocket) -> None:
        """Register client connection for a symbol and send initial snapshot."""
        clean_symbol = symbol.upper().replace(".NS", "").replace("NSE:", "").strip()
        await websocket.accept()

        if clean_symbol not in self.connections:
            self.connections[clean_symbol] = set()
        self.connections[clean_symbol].add(websocket)

        logger.info(f"Client connected to /ws/{clean_symbol}. Active subscribers: {len(self.connections[clean_symbol])}")

        # Send initial snapshot immediately
        initial_tick = await self.get_latest_tick_snapshot(clean_symbol)
        try:
            await websocket.send_text(json.dumps(initial_tick))
        except Exception as e:
            logger.warning(f"Failed sending initial tick to {clean_symbol}: {e}")

        # Ensure background tick engine is running
        self.ensure_tick_engine_started()

    def disconnect(self, symbol: str, websocket: WebSocket) -> None:
        """Unregister client connection."""
        clean_symbol = symbol.upper().replace(".NS", "").replace("NSE:", "").strip()
        if clean_symbol in self.connections:
            self.connections[clean_symbol].discard(websocket)
            if not self.connections[clean_symbol]:
                del self.connections[clean_symbol]
        logger.info(f"Client disconnected from /ws/{clean_symbol}.")

    async def broadcast_tick(self, symbol: str, tick: Dict[str, Any]) -> None:
        """Broadcast tick message to all active WebSocket connections for the symbol."""
        clean_symbol = symbol.upper().replace(".NS", "").replace("NSE:", "").strip()
        self.latest_quotes[clean_symbol] = tick

        subscribers = self.connections.get(clean_symbol, set()).copy()
        if not subscribers:
            return

        dead_sockets = set()
        payload = json.dumps(tick)

        for ws in subscribers:
            try:
                await ws.send_text(payload)
            except (WebSocketDisconnect, RuntimeError):
                dead_sockets.add(ws)
            except Exception as e:
                logger.warning(f"Error broadcasting to socket for {clean_symbol}: {e}")
                dead_sockets.add(ws)

        # Cleanup disconnected sockets
        for ws in dead_sockets:
            self.disconnect(clean_symbol, ws)

    async def get_latest_tick_snapshot(self, symbol: str) -> Dict[str, Any]:
        """Fetch or construct current tick payload for symbol."""
        clean_symbol = symbol.upper().replace(".NS", "").replace("NSE:", "").strip()
        cached = self.latest_quotes.get(clean_symbol)
        now_utc = datetime.now(timezone.utc)

        if cached:
            # Preserve authentic observation timestamp, record served/fetch time
            snapshot = dict(cached)
            snapshot["served_at"] = now_utc.isoformat()
            return snapshot

        # Fetch from real market provider
        q = await self.provider.get_latest_quote(clean_symbol)
        if not q or not getattr(q, "price", None) or q.price <= 0:
            return {
                "symbol": clean_symbol,
                "status": "UNAVAILABLE",
                "message": f"Verified market quote unavailable for '{clean_symbol}'",
                "ltp": None,
                "open": None,
                "high": None,
                "low": None,
                "close": None,
                "volume": 0,
                "source": "NONE",
                "freshness": "UNAVAILABLE",
                "observed_at": None,
                "fetch_timestamp": now_utc.isoformat(),
            }

        price = float(q.price)
        open_price = float(q.open_price) if q.open_price else price
        high_price = float(q.high_price) if q.high_price else price
        low_price = float(q.low_price) if q.low_price else price
        close_price = float(getattr(q, "close_price", None) or price)
        obs_dt = q.observed_at.replace(tzinfo=timezone.utc) if q.observed_at.tzinfo is None else q.observed_at

        tick = {
            "symbol": clean_symbol,
            "ltp": round(price, 2),
            "open": round(open_price, 2),
            "high": round(high_price, 2),
            "low": round(low_price, 2),
            "close": round(close_price, 2),
            "volume": getattr(q, "volume", 0) or 0,
            "source": q.source,
            "freshness": getattr(q, "freshness_status", "END_OF_DAY"),
            "CurrentBarUnixTime": int(obs_dt.timestamp()),
            "observed_at": obs_dt.isoformat(),
            "fetch_timestamp": now_utc.isoformat(),
        }
        self.latest_quotes[clean_symbol] = tick
        return tick


    def ensure_tick_engine_started(self) -> None:
        """Start background simulation engine if not already running."""
        if not self._simulation_task or self._simulation_task.done():
            self._is_running = True
            try:
                loop = asyncio.get_running_loop()
                self._simulation_task = loop.create_task(self._run_simulation_loop())
            except RuntimeError:
                pass

    async def _run_simulation_loop(self) -> None:
        """Emit periodic ticks for subscribed symbols using genuine observations from supported backend sources."""
        while self._is_running:
            try:
                active_symbols = list(self.connections.keys())
                for symbol in active_symbols:
                    if not self.connections.get(symbol):
                        continue

                    if self.enable_demo_simulation:
                        # Explicitly separated and labelled demonstration simulation ONLY when explicitly enabled
                        current = await self.get_latest_tick_snapshot(symbol)
                        cur_price = current.get("ltp")
                        if cur_price is not None:
                            delta_pct = (random.random() - 0.49) * 0.003
                            new_price = round(cur_price * (1.0 + delta_pct), 2)
                            now_utc = datetime.now(timezone.utc)
                            tick = {
                                "symbol": symbol,
                                "ltp": new_price,
                                "open": current.get("open", new_price),
                                "high": max(current.get("high", new_price), new_price),
                                "low": min(current.get("low", new_price), new_price),
                                "close": new_price,
                                "volume": current.get("volume", 0) + random.randint(10, 100),
                                "source": "DEMO_SIMULATION_FIXTURE",
                                "freshness": "SIMULATED",
                                "CurrentBarUnixTime": int(now_utc.timestamp()),
                                "observed_at": now_utc.isoformat(),
                            }
                            await self.broadcast_tick(symbol, tick)
                        continue

                    from backend.app.services.angel_adapter import is_nse_market_open

                    # 1. Market Closed Check (09:15 - 15:30 IST, Mon-Fri): do not spin live loop, serve cached
                    if not is_nse_market_open():
                        cached = self.latest_quotes.get(symbol)
                        if cached and cached.get("ltp") is not None:
                            closed_tick = dict(cached)
                            closed_tick["served_from_cache"] = True
                            closed_tick["freshness"] = "CLOSED"
                            closed_tick["data_status"] = "stale"
                            await self.broadcast_tick(symbol, closed_tick)
                        continue

                    # 2. Normal Operation: Fetch from active provider
                    q = await self.provider.get_latest_quote(symbol)
                    now_utc = datetime.now(timezone.utc)
                    if not q or not getattr(q, "price", None) or q.price <= 0:
                        cached = self.latest_quotes.get(symbol)
                        if cached and cached.get("ltp") is not None:
                            # Both socket & REST down: serve last cached quote with served_from_cache=True, REAL timestamp, data_status="stale"
                            stale_tick = dict(cached)
                            stale_tick["served_from_cache"] = True
                            stale_tick["data_status"] = "stale"
                            stale_tick["freshness"] = "STALE"
                            stale_tick["fetch_timestamp"] = now_utc.isoformat()
                            await self.broadcast_tick(symbol, stale_tick)
                            continue

                        tick = {
                            "symbol": symbol,
                            "status": "UNAVAILABLE",
                            "message": f"Verified market quote unavailable for '{symbol}'",
                            "ltp": None,
                            "open": None,
                            "high": None,
                            "low": None,
                            "close": None,
                            "volume": 0,
                            "source": "NONE",
                            "freshness": "UNAVAILABLE",
                            "data_status": "unavailable",
                            "observed_at": None,
                            "fetch_timestamp": now_utc.isoformat(),
                        }
                        self.latest_quotes[symbol] = tick
                        await self.broadcast_tick(symbol, tick)
                        continue

                    # Genuine observation from supported provider
                    obs_dt = (
                        q.observed_at.replace(tzinfo=timezone.utc)
                        if q.observed_at.tzinfo is None
                        else q.observed_at
                    )
                    freshness = (
                        "STALE"
                        if (q.is_stale or q.data_status == "stale")
                        else ("DELAYED" if q.is_delayed else getattr(q, "freshness_status", "CURRENT"))
                    )
                    price = float(q.price)
                    tick = {
                        "symbol": symbol,
                        "status": "AVAILABLE",
                        "ltp": round(price, 2),
                        "open": round(float(q.open_price), 2) if q.open_price else round(price, 2),
                        "high": round(float(q.high_price), 2) if q.high_price else round(price, 2),
                        "low": round(float(q.low_price), 2) if q.low_price else round(price, 2),
                        "close": round(float(getattr(q, "close_price", None) or price), 2),
                        "volume": getattr(q, "volume", 0) or 0,
                        "source": q.source,
                        "freshness": freshness,
                        "CurrentBarUnixTime": int(obs_dt.timestamp()),
                        "observed_at": obs_dt.isoformat(),
                        "fetch_timestamp": now_utc.isoformat(),
                    }
                    await self.broadcast_tick(symbol, tick)

                await asyncio.sleep(2.0)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"MarketHub loop error: {e}")
                await asyncio.sleep(2.0)


# Singleton Hub instance
market_hub = MarketHub()


def get_market_hub() -> MarketHub:
    """FastAPI Dependency for MarketHub singleton."""
    return market_hub
