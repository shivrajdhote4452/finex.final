# FinEx — Go-Live & Demo Runbook Checklist

**Date:** 25 October 2026 (Updated for Demo-Readiness)  
**Target Milestone:** Demo Handoff (10 November 2026)  
**System Universe:** Indian NSE Equities & Educational Paper Trading  
**Status:** FULLY GREEN — All CI Quality Gates Passing  

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
   - Ticks are broadcast in real time to connected web clients over `/api/v1/market/ws/{symbol}` without unstable background client socket threads.

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
> See full step-by-step presentation script in [docs/demo-runbook.md](../demo-runbook.md).

### Demo Runbook Script for Closed Market:

1. **Trade Time Machine (PR #15 — Primary Demo Engine):**
   - Click `Charts` → `⏳ Time Machine Replay`.
   - Point out holiday awareness: selecting `2026-11-10` triggers the honest holiday notice (`Diwali–Balipratipada (Demo Day — Market Closed)`).
   - Rewind to verified trading day: **Friday 16 October 2026**.
   - Press `Play` (or `4x` speed), watch 5-minute candles form chronologically, pause, and execute paper buy/sell orders priced at authentic replay candle closes against the ₹10,00,000 wallet with persistent badge: `REPLAY — <symbol> — <date> — past NSE data, not live`.

2. **Option B Native Chart Honesty (PR #19):**
   - Demonstrate the `FinEx Live (Angel One)` toggle.
   - When market is closed/empty, chart renders `FALLBACK_CACHED` with genuine observation timestamp ribbon (`ℹ️ Last real data: <date time>`).
   - If no cached data exists, renders honest empty state (`No market data available for this symbol`), status `DISCONNECTED`, zero `Math.random` calls.
   - Demo synthesizer is gated behind `VITE_DEMO_SIMULATION=false` (default off). When turned on, renders prominent red watermark banner: `⚠️ SIMULATED DATA — randomly generated for display only, not market prices`.

3. **TradingView Pro Integration:**
   - Switch between native FinEx lightweight-charts engine and embedded TradingView Pro widget via the toolbar toggle.

4. **Paper Trading on Real Historical & Cached Observations:**
   - Execute paper buy and sell orders on `RELIANCE` and `TCS`.
   - Portfolio ledger entries, holdings valuation, cash deductions, and P&L calculations execute accurately against authentic market observations.

---

## 4. Architecture & Security Checklist

- [x] **Zero Secrets in Repository (PR #20):** Gitleaks v8.30.1 audit across all 104 commits verified clean (`docs/secrets-scan-report.md`). Confirmed `.env` has never been committed.
- [x] **ADR Scope Decisions Closed (PR #19):** ADR-006 (Flutter mobile packaging) and ADR-007 (Databricks Delta Lake) formally marked `DECIDED (DEFER)` to post-demo, guaranteeing 100% focus on web terminal stability.
- [x] **Synthesizer Option B Implemented (PR #19):** Cached-first fallback, demo simulation flag gate, full-width watermark banner, and honest empty state.
- [x] **Demo-Blocker Issues Pruned (PR #21):** Pruned to 3 genuinely open issues (branch protection, cached-mode rehearsal, clean-machine verification), 2 done, 1 stale. Split issue files prepared in `docs/issues/`.
- [x] **Clean-Machine Rehearsal Verified (CORR-9):** Cloned into fresh isolated directory from docs alone, installed strictly from `backend/requirements.lock`, migrated fresh database to head (revisions 001–007), verified 62.33% coverage, passed 10/10 AI tests and 30/30 prompt evals, built web bundle in 2.61s, and confirmed all HTTP and WebSocket endpoints ([`docs/clean-machine-rehearsal-report.md`](../clean-machine-rehearsal-report.md)).
- [x] **CI Pipeline Fully Green (PR #18):** `pytest -m "not live"` with `--cov-fail-under=60` baseline floor. All 168 backend tests, 10 AI tests, and 30 AI evaluation cases passing.
- [x] **Dependencies Pinned:** Locked dependencies in `backend/requirements.lock`.

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
