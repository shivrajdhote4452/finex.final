"""Angel One SmartAPI Market Data & WebSocket Adapter.

Task: FinEx Real-Time Market Data & Live Charting Specification
Implements:
- Headless TOTP login via pyotp
- Historical candle data via SmartConnect.getCandleData
- Live quote ticks via SmartWebSocketV2
"""

import logging
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

import pyotp
from backend.app.config import get_settings

logger = logging.getLogger(__name__)

# Try importing SmartApi; handle gracefully if environment issues arise
try:
    from SmartApi import SmartConnect
    from SmartApi.smartWebSocketV2 import SmartWebSocketV2
except ImportError:
    SmartConnect = None
    SmartWebSocketV2 = None
    logger.warning("SmartApi package is not available or incomplete.")

# Canonical 5 verified NSE instruments specified + extended top Nifty leaders
FINEX_INSTRUMENTS: Dict[str, str] = {
    "RELIANCE": "2885",
    "TCS": "11536",
    "HDFCBANK": "1333",
    "INFY": "1594",
    "ICICIBANK": "4963",
    "SBIN": "3045",
    "BHARTIARTL": "10604",
    "ITC": "1660",
    "LT": "11483",
    "TATASTEEL": "3499",
    "TATAMOTORS": "3456",
    "MARUTI": "10999",
    "WIPRO": "3787",
    "HCLTECH": "7229",
}

TOKEN_TO_SYMBOL: Dict[str, str] = {v: k for k, v in FINEX_INSTRUMENTS.items()}

# SmartAPI Candle Interval Map
INTERVAL_MAP = {
    "1m": "ONE_MINUTE",
    "ONE_MINUTE": "ONE_MINUTE",
    "3m": "THREE_MINUTE",
    "5m": "FIVE_MINUTE",
    "10m": "TEN_MINUTE",
    "15m": "FIFTEEN_MINUTE",
    "30m": "THIRTY_MINUTE",
    "1h": "ONE_HOUR",
    "ONE_HOUR": "ONE_HOUR",
    "1D": "ONE_DAY",
    "ONE_DAY": "ONE_DAY",
}


class AngelOneMarketAdapter:
    """Production-grade Angel One SmartAPI connector with graceful fallback."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        client_id: Optional[str] = None,
        mpin: Optional[str] = None,
        totp_secret: Optional[str] = None,
    ):
        settings = get_settings()
        self.api_key = api_key or getattr(settings, "ANGEL_API_KEY", "") or ""
        self.client_id = client_id or getattr(settings, "ANGEL_CLIENT_ID", "") or ""
        self.mpin = mpin or getattr(settings, "ANGEL_MPIN", "") or ""
        self.totp_secret = totp_secret or getattr(settings, "ANGEL_TOTP_SECRET", "") or ""

        self.smart_api = SmartConnect(api_key=self.api_key) if (SmartConnect and self.api_key) else None
        self.jwt_token: Optional[str] = None
        self.feed_token: Optional[str] = None
        self.refresh_token: Optional[str] = None

    def is_configured(self) -> bool:
        """Verify if Angel One credentials are valid and ready."""
        required = [self.api_key, self.client_id, self.mpin, self.totp_secret]
        for val in required:
            if not val or "your_" in val.lower() or "placeholder" in val.lower():
                return False
        return len(self.api_key) >= 5 and len(self.totp_secret) >= 8

    def authenticate(self) -> bool:
        """Perform headless 2FA TOTP authentication to generate JWT session."""
        if not self.is_configured():
            logger.info("Angel One credentials not configured. Live Angel API authentication skipped.")
            return False

        if not self.smart_api:
            self.smart_api = SmartConnect(api_key=self.api_key)

        try:
            totp_code = pyotp.TOTP(self.totp_secret).now()
            session = self.smart_api.generateSession(self.client_id, self.mpin, totp_code)

            if not session or not session.get("status"):
                err_msg = session.get("message") if session else "Unknown error"
                logger.error(f"Angel One login failed: {err_msg}")
                raise RuntimeError(f"Angel One login failed: {err_msg}")

            data = session.get("data", {})
            self.jwt_token = data.get("jwtToken")
            self.refresh_token = data.get("refreshToken")
            self.feed_token = self.smart_api.getfeedToken()
            logger.info(f"Angel One SmartAPI authenticated successfully for client {self.client_id}")
            return True
        except Exception as e:
            logger.error(f"Angel One authentication error: {e}")
            raise

    def get_historical_candles(
        self,
        symbol: str,
        interval: str,
        from_date: str,
        to_date: str,
    ) -> List[Dict[str, Any]]:
        """Fetch historical OHLCV candle data from Angel One SmartAPI."""
        clean_symbol = symbol.upper().replace(".NS", "").replace("NSE:", "").strip()
        if clean_symbol not in FINEX_INSTRUMENTS:
            raise ValueError(f"Symbol '{symbol}' not supported by Angel One NSE registry.")

        if not self.jwt_token:
            self.authenticate()

        if not self.smart_api:
            raise RuntimeError("SmartAPI client not initialized.")

        token = FINEX_INSTRUMENTS[clean_symbol]
        smart_interval = INTERVAL_MAP.get(interval, "ONE_DAY")

        params = {
            "exchange": "NSE",
            "symboltoken": token,
            "interval": smart_interval,
            "fromdate": from_date,
            "todate": to_date,
        }

        res = self.smart_api.getCandleData(params)
        if not res or not res.get("status") or not res.get("data"):
            err_msg = res.get("message") if res else "Empty response"
            raise ValueError(f"Unable to fetch candles for {clean_symbol} from Angel One: {err_msg}")

        candles = []
        for row in res["data"]:
            try:
                # row format: [timestamp_str, open, high, low, close, volume]
                iso_str = row[0]
                unix_ts = int(datetime.fromisoformat(iso_str).timestamp())
                candles.append(
                    {
                        "time": unix_ts,
                        "open": float(row[1]),
                        "high": float(row[2]),
                        "low": float(row[3]),
                        "close": float(row[4]),
                        "volume": int(row[5]),
                    }
                )
            except Exception as parse_err:
                logger.warning(f"Failed parsing candle row {row}: {parse_err}")
                continue

        return candles

    def start_live_stream(self, on_tick_callback: Callable[[Any], None]) -> Optional[Any]:
        """Start SmartWebSocketV2 streaming in Quote Feed Mode 2."""
        if not self.is_configured():
            logger.info("Angel One credentials not configured. Native live stream disabled.")
            return None

        if not self.jwt_token or not self.feed_token:
            self.authenticate()

        if not SmartWebSocketV2:
            logger.error("SmartWebSocketV2 class is not available.")
            return None

        sws = SmartWebSocketV2(self.jwt_token, self.api_key, self.client_id, self.feed_token)
        token_list = [{"exchangeType": 1, "tokens": list(FINEX_INSTRUMENTS.values())}]

        def on_open(wsapp):
            logger.info("Angel One SmartWebSocketV2 connected. Subscribing to token list...")
            sws.subscribe("finex_live_stream", 2, token_list)

        def on_data(wsapp, message):
            on_tick_callback(message)

        def on_error(wsapp, error):
            logger.error(f"Angel One SmartWebSocketV2 error: {error}")

        def on_close(wsapp):
            logger.info("Angel One SmartWebSocketV2 closed.")

        sws.on_open = on_open
        sws.on_data = on_data
        sws.on_error = on_error
        sws.on_close = on_close

        try:
            sws.connect()
            return sws
        except Exception as e:
            logger.error(f"Failed connecting to SmartWebSocketV2: {e}")
            return None
