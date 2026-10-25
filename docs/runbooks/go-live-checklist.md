# FinEx — Go-Live & Demo Runbook Checklist

**Date:** 19 October 2026  
**Target Milestone:** Demo Handoff (10 November 2026)  
**System Universe:** Indian NSE Equities & Educational Paper Trading  

---

## 1. Angel One SmartAPI Credential Provisioning

1. **SmartAPI Developer Account Setup:**
   - Log into [SmartAPI Portal](https://smartapi.angelone.in/).
   - Ensure an application named `Finex` is active with an allocated `API_KEY`.
   - Ensure your client code (`ANGEL_CLIENT_ID`) and PIN (`ANGEL_MPIN`) are verified.

2. **Static IP Binding & Restriction:**
   > [!IMPORTANT]
   > Angel One enforces static IP whitelisting for all SmartAPI requests.
   > **Critical Limitation:** Angel One allows modifying your registered static public IP **only once every 7 days**.
   > If using a dynamic broadband connection (e.g., Jio, Airtel), verify your public IPv4 (`curl ifconfig.me`) before the morning session. If hosting on a cloud instance (AWS/GCP/Azure), attach an Elastic/Static IP address.

3. **TOTP Two-Factor Authentication:**
   - Scan the QR code or register the base32 TOTP secret key (`ANGEL_TOTP_SECRET`) into an authenticator app (Google Authenticator / 1Password / Bitwarden).
   - Ensure the server system clock is synced via NTP (max drift < 30 seconds).

4. **Environment Variables Configuration:**
   - Add to local `.env` (gitignored, never committed to VCS):
     ```env
     MARKET_DATA_MODE=INDIAN_LIVE_DATA
     ANGEL_API_KEY=YOUR_PROVISIONED_API_KEY
     ANGEL_CLIENT_ID=YOUR_CLIENT_CODE
     ANGEL_MPIN=YOUR_FOUR_DIGIT_MPIN
     ANGEL_TOTP_SECRET=YOUR_BASE32_TOTP_SECRET
     ```

---

## 2. Daily Session Refresh Lifecycle (Pre-Market 09:00 IST)

Angel One JWT tokens expire every 24 hours. The application handles authentication and session regeneration through the following protocol:

1. **Boot Time Authentication:**
   - When `MARKET_DATA_MODE=INDIAN_LIVE_DATA`, `backend/app/factory.py` authenticates with Angel One SmartAPI at startup using headless TOTP generation.
   - Bad credentials immediately raise a `RuntimeError` to prevent silent boot failures.

2. **Automatic 401 Session Recovery:**
   - If an active token expires mid-session with error code `AG8001` or HTTP 401, `AngelOneMarketAdapter._fetch_ltp_with_retry` and `getCandleData` automatically trigger `authenticate()`, generate a new JWT and feed token, and retry the request without dropping the client stream.

3. **2-Second REST Polling Architecture by Design:**
   - To ensure maximum deterministic reliability during the demo handoff, FinEx uses a 2-second REST polling pipeline (`ltpData`) through `MarketHub`.
   - Every tick receives verified SHA-256 evidence, automatic tenacity retry with exponential backoff, and circuit breaker protection (5 consecutive failures trip a 60s fast-degrade cooldown).
   - Ticks are broadcast in real time to connected web and mobile clients over `/api/v1/market/ws/{symbol}` without unstable background client socket threads.

4. **Scheduled Daily Warmup (Cron / Task Scheduler):**
   - For 24/7 deployments, execute a daily health check curl at 08:50 IST:
     ```bash
     curl -s http://127.0.0.1:8000/api/v1/market/quotes/RELIANCE
     ```

---

## 3. Demo Strategy for 10 November 2026 (Diwali–Balipratipada)

> [!WARNING]
> **Market Closed Calendar Notice:**  
> **10 November 2026 is Diwali–Balipratipada (National Stock Exchange Holiday).**  
> Indian equity markets are completely closed. Real-time live exchange ticks will not be transmitted on this date.
> Under FinEx's strict Data Honesty Policy, the application will **NEVER** fabricate synthetic fluctuations or present stale prices as live.

### Demo Runbook Script for Closed Market:

1. **Honesty Policy & Status Indicators:**
   - Show the top header status badge displaying `Angel One SmartAPI (Live NSE Feed)`.
   - Highlight the **`CACHED`** / **`CLOSED`** status pill next to the price quote:
     - Point out that the quote displays its genuine last observation timestamp (`observed_at`).
     - Point out `served_from_cache: true` and `data_status: "stale"` / `freshness: "CLOSED"`.
   - Explain to evaluators: *"FinEx strictly obeys SEBI guidelines and data provenance standards: when the exchange is closed or the feed is unavailable, we explicitly show cached status with real timestamps rather than simulating fake movements."*

2. **FinEx Live Chart vs TradingView Pro:**
   - Demonstrate the **`FinEx Live (Angel One) | TradingView Pro`** segmented toggle on the charts workspace.
   - Switch between the native FinEx lightweight-charts candlestick engine (with interval bucketing and historical candles) and the embedded TradingView Pro widget.

3. **Paper Trading on Real Historical & Cached Observations:**
   - Execute paper buy and sell orders on `RELIANCE` and `TCS`.
   - Show that portfolio ledger entries, holdings valuation, cash deductions, and P&L calculations execute accurately against authentic market observations.

4. **Multi-Mode Fallback Demonstration:**
   - Demonstrate mode switching to `INDIA_HISTORICAL_REPLAY` (showing SEBI 30-day educational lag with deterministic historical candle playback).

---

## 4. Secret Sanitation & Auditing Checklist

- [x] Verified `.env` is listed in `.gitignore` and has never been committed.
- [x] Executed git log pattern scan for Google API keys (`AIza...`) — **0 matches found**.
- [x] Executed deep regex scan on full git history for API keys, TOTP secrets, and credentials — **0 leaked secrets found**.
- [x] Verified `.env.example` contains only placeholder tokens (`YOUR_ANGEL_API_KEY_HERE`, etc.).
- [x] CI pipeline configured with `pytest -m "not live"` and `--cov-fail-under=60` (baseline floor; measured coverage ~62%).
- [x] Backend dependencies pinned in `backend/requirements.lock`.

---

## 5. Quick Verification Commands

```powershell
# 1. Verify Angel One credentials & live quote
$env:PYTHONPATH="."; & ".\.venv\Scripts\python.exe" -c "
from backend.app.config import get_settings
from backend.app.services.angel_adapter import AngelOneMarketAdapter
import asyncio
s = get_settings()
print('Mode:', s.MARKET_DATA_MODE)
a = AngelOneMarketAdapter()
print('Configured:', a.is_configured(), 'Auth:', a.authenticate())
print('RELIANCE:', asyncio.run(a.get_latest_quote('RELIANCE')).price)
"

# 2. Run offline tests
& ".\.venv\Scripts\python.exe" -m pytest backend/tests/test_angel_smartapi_market_data.py -q -m "not live"

# 3. Check live backend API
curl.exe -s http://127.0.0.1:8000/api/v1/market/mode
curl.exe -s http://127.0.0.1:8000/api/v1/market/quotes/RELIANCE
```
