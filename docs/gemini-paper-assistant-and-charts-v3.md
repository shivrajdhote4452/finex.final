# FinEx Revision 3: Gemini AI Paper Assistant, Market Data Engine & TradingView-Style Chart Workspace

**Target Date:** 10 November 2026  
**Document Author:** Antigravity Implementation Engineer  
**Prepared For:** Shivraj Dhote  
**Branch:** `feat/gemini-paper-trading-charts` (based on `main` @ `e53f479`)  
**Design Paradigm:** Pure Black `#000000` Graphite Terminal Canvas with Warm Amber `#F29A60` Action Accents  

---

## 1. Executive Summary & Customer Experience

Revision 3 delivers an end-to-end, high-precision educational paper investment experience for FinEx without disrupting existing operational PostgreSQL records, user profiles, or Graphite Terminal styling:

1. **Multilingual Gemini Paper Investment Assistant:**
   - Interprets natural language queries in **English**, **Hindi (Devanagari)**, and **Hinglish (Latin script)**.
   - Grounded tool execution using Google's current `google-genai` SDK with typed schemas.
   - Derives authenticated ownership from cryptographically verified server-side JWT session context.
   - Enforces an architectural separation of concerns:
     - **Research Requests** (e.g. *"Which stocks should I consider for my paper portfolio?"*): create **zero orders**, explain observations, citation dates, fundamentals, and risk constraints.
     - **Execution Requests** (e.g. *"Invest INR 10,000 of my virtual balance across RELIANCE and TCS"*): construct a **server-validated, bounded Paper Investment Proposal** with strict 10-minute expiry, virtual cash reservations, and atomic fill recording.
     - **Active Chart Context:** automatically ingests symbol, timeframe, visible price, and active technical indicator values via `get_chart_context`.
2. **Deterministic Genuine Market Data Engine & Data Modes:**
   - **`INDIA_HISTORICAL_REPLAY` (Default Indian Mode):** Enforces SEBI Circular (8 May 2026, effective 1 July 2026) compliance requiring a 30-day data lag for educational use. Bounded historical replay clock ensures zero future lookahead bias in both indicator calculation and simulated paper fills.
   - **`US_ALPACA_PAPER` (Opt-in USD Demonstration):** Strictly isolated paper execution backend with a paper-only host allowlist (`paper-api.alpaca.markets`, `data.alpaca.markets`). Rejects live brokerage order hosts (`api.alpaca.markets`) at startup. Clearly labeled **"Live IEX (USD Paper)"** with explicit USD currency boundaries.
   - **`INDIAN_LIVE_DATA` (Future / Disabled):** Technical scaffolding prepared for Upstox V3 / Analytics Token, but disabled by default due to undocumented virtual trading distribution rights.
3. **TradingView-Style Analytical Chart Workspace (Sections 8A–8K):**
   - **Web Frontend (`web/src/pages/ChartWorkspaceScreen.tsx`):** Built with TradingView `lightweight-charts` v4.2.1 pinned. Features symbol selection, 7 timeframes (`1m` to `1M`), 4 chart types (Candlestick, Bar, Line, Area), volume histogram overlay, technical indicators (SMA, EMA, Bollinger Bands, RSI, MACD, VWAP), drawing tools with time/price coordinate persistence, multi-chart layout presets, collapsible order dock, and integrated "Ask FinEx AI" panel.
   - **Mobile Flutter (`mobile/lib/screens/chart_screen.dart`):** Interactive mobile canvas painter with touch crosshair HUD, timeframe selectors, bottom sheet paper order ticket, and Gemini chat drawer.

---

## 2. Changed Files & Database Migrations

### 2.1 Database Migrations & Schemas
- **Alembic Migration:** `alembic/versions/6d8e21a9f023_005_chart_proposals_replay.py`
  - `paper_proposals`: stores bounded proposals, proposed allocations, reserved budgets, currency, status (`PROPOSED`, `EXECUTED`, `EXPIRED`, `REJECTED`), and timestamps.
  - `chart_layouts`: multi-chart layout arrangements (`single`, `dual_h`, `dual_v`, `quad`), active symbols, and crosshair sync options.
  - `chart_drawings`: trend lines, rays, horizontal lines, rectangles, Fibonacci levels anchored to `(time, price)` coordinates.
  - `chart_indicator_templates`: user-saved technical indicator configurations.
  - `replay_sessions`: historical replay clock, start/end boundaries, and playback speed.
- **SQL Initialization:** `data/init_finex_db.sql` updated with all 5 new tables, indexes, and updated baseline version stamp `6d8e21a9f023`.

### 2.2 Backend Codebase
- `backend/app/config.py` & `.env.example`: added `GEMINI_API_KEY`, `GEMINI_MODEL`, `MARKET_DATA_MODE`, `SEBI_EDUCATIONAL_LAG_DAYS`, `ALPACA_API_KEY`, `ALPACA_SECRET_KEY`, `ALPACA_BASE_URL`.
- `backend/app/ports/market_data.py`: extended `MarketHistoryPoint` with `time: Optional[int]`, `as_of: Optional[datetime]`, and `interval: str = "1D"`.
- `backend/app/domain/technical_indicators.py`: deterministic implementations of SMA, EMA, Bollinger Bands, Wilder's RSI, MACD (12/26/9), and session VWAP with proper warm-up `None` values.
- `backend/app/domain/gemini_assistant.py`: 11 typed tool definitions, multilingual detection, bounded proposal generation, chart context inspection, and graceful unconfigured key degradation.
- `backend/app/adapters/alpaca_paper_adapter.py`: paper host security allowlist, asset search, latest IEX quotes, and paper order execution.
- `backend/app/adapters/market_data_provider.py`: DB history fetching, `as_of` replay clock filtering, and DB quote seeding.
- `backend/app/routers/charts.py`: REST routes for layouts, drawings, templates, and replay session clock management.
- `backend/app/routers/gemini_assistant.py`: assistant chat, proposal listing, proposal execution, and status endpoints.
- `backend/app/routers/market.py`: added `/market/mode` and `/market/indicators/{symbol}`.
- `backend/app/factory.py`: mounted chart and assistant routers.
- `backend/tests/test_gemini_paper_assistant_and_charts.py`: 9 comprehensive integration and security acceptance tests.

### 2.3 Web Frontend (`web/`)
- `web/package.json`: pinned `lightweight-charts@4.2.1`.
- `web/src/api/client.ts`: added `market`, `charts`, and `geminiAssistant` API namespaces.
- `web/src/pages/ChartWorkspaceScreen.tsx`: complete TradingView-style analytical workspace.
- `web/src/components/layout/AppShell.tsx`: added `Charts` navigation tab.
- `web/src/App.tsx`: wired `ChartWorkspaceScreen` route.

### 2.4 Mobile Flutter (`mobile/`)
- `mobile/pubspec.yaml`: added `webview_flutter: ^4.14.1`.
- `mobile/lib/services/api_client.dart`: added `getMarketHistory`, `getIndicators`, `getMarketMode`, `sendGeminiAssistantMessage`, and `executeProposal`.
- `mobile/lib/screens/chart_screen.dart`: mobile interactive candlestick painter, indicators, order ticket sheet, and Gemini assistant drawer.
- `mobile/lib/screens/more_screen.dart`: added `TradingView Chart Workspace` module navigation.
- `mobile/lib/screens/markets_screen.dart`: added `Open Interactive Chart` button to stock detail sheets.

---

## 3. Gemini API-Key Setup Instructions

FinEx enforces strict credential isolation. The API key is stored only in your local environment configuration and is never logged, sent in chat, or bundled into client code.

### Step 1: Obtain a New Gemini API Key
1. Visit **Google AI Studio**: [https://aistudio.google.com/](https://aistudio.google.com/)
2. Click **Get API key** and generate a new key for your Google Cloud / AI Studio project.
3. *Note: If an older key was exposed or pasted into conversation, revoke it immediately in Google AI Studio.*

### Step 2: Configure Key Locally in `.env`
In your project root directory `f:\Project File\Finex Final\`, open your local `.env` file (or copy `.env.example` to `.env` if not already present) and set:
```bash
GEMINI_API_KEY=YOUR_ACTUAL_NEW_KEY_HERE
GEMINI_MODEL=gemini-1.5-flash
```

### Step 3: Unconfigured State & Safety Verification
- When `GEMINI_API_KEY` is missing or contains the placeholder `YOUR_NEW_GEMINI_API_KEY_HERE`, the FastAPI backend **never crashes** and **never fabricates responses**.
- The endpoint `GET /api/v1/ai/assistant/status` cleanly returns:
  ```json
  {
    "gemini_configured": false,
    "status_message": "Gemini API key is not configured. Please set GEMINI_API_KEY in your local .env configuration.",
    "market_mode": "INDIA_HISTORICAL_REPLAY"
  }
  ```
- The chat interface informs the user clearly: *"Gemini Assistant setup incomplete. Please add GEMINI_API_KEY to your local .env"*.

---

## 4. Market Data Modes & Simulation Assumptions

| Mode | Currency | Feeds & Providers | Regulatory / Compliance Rules | Simulation & Fill Model |
| :--- | :--- | :--- | :--- | :--- |
| **`INDIA_HISTORICAL_REPLAY`** *(Default)* | INR | Genuine NSE historical daily & intraday observations in PostgreSQL | **SEBI Circular 8 May 2026:** Enforces 30-day educational data lag. No observations after `simulated_clock` are accessible. | Long-only cash paper engine. Fills at next eligible observation at or after simulated order submission. Deducts 0.05% simulated STT/brokerage. |
| **`US_ALPACA_PAPER`** *(Opt-in Demo)* | USD | Live IEX market data feed via Alpaca Basic Plan (up to 30 streaming symbols) | Strictly personal development account. Basic IEX coverage is partial US exchange data, not consolidated SIP. Refuses live hosts at startup. | Independent USD virtual account. Fills executed via Alpaca Paper API or local IEX quotes with clear feed labeling. |
| **`INDIAN_LIVE_DATA`** *(Future)* | INR | Upstox Analytics Token / Market Data V3 | Blocked until explicit written virtual trading and redistribution rights are confirmed. Scraping / unofficial proxies forbidden. | Disabled in backend configuration. |

---

## 5. Chart Feature Matrix (Sections 8A–8K)

| Feature | Category | Implementation Details |
| :--- | :--- | :--- |
| **Candlestick, Bar, Line, Area** | Library-provided & Custom | Rendered via `lightweight-charts` v4 with pure black `#000000` canvas and custom theme tokens. |
| **Volume Histogram** | Custom Pane | Semi-transparent volume bars color-coded by bar direction. |
| **SMA (20, 50, 200)** | Custom Engine | Deterministic Python backend (`calculate_sma`) + TypeScript client overlay. Exact mathematical mean. |
| **EMA (20, 50, 200)** | Custom Engine | Exponential smoothing with $\alpha = \frac{2}{N+1}$, seeded by initial SMA. |
| **Bollinger Bands (20, 2.0)** | Custom Engine | Middle SMA(20) $\pm$ 2.0 sample standard deviations. Upper and lower bands. |
| **RSI (14)** | Custom Engine | J. Welles Wilder's smoothed RSI. Unavailable / `None` until warm-up bar 14. |
| **MACD (12, 26, 9)** | Custom Engine | Fast EMA(12) minus Slow EMA(26), 9-period signal line, and difference histogram. |
| **Session VWAP** | Custom Engine | $\frac{\sum (\text{Typical Price} \times \text{Volume})}{\sum \text{Volume}}$ reset at session boundaries. |
| **Persistent Drawings** | Custom Backend + UI | Trend Line, Horizontal Line, Ray, Rectangle, Fibonacci Retracement anchored to `(time, price)` coordinates in PostgreSQL table `chart_drawings`. |
| **Multi-Chart Layouts** | Custom Layout Engine | `single`, `dual_h`, `dual_v`, `quad` layout presets saved to PostgreSQL table `chart_layouts`. |
| **Historical Replay Session** | Custom Engine | Simulated clock, play/pause controls, speed multiplier (1x, 2x, 5x) persisted in `replay_sessions`. |
| **Paper Order Overlays** | Custom Integration | Chart entry markers (Green arrow for Buy, Red arrow for Sell) loaded directly from `paper_trades` table. |
| **Gemini Active Chart Context** | Custom Tool Integration | `get_chart_context` inspects active symbol, timeframe, visible price, and indicators to ground AI explanations. |
| **Required Attribution** | Compliance | Visible persistent notice: *"TradingView Lightweight Charts™ • Genuine Market Data Engine"*. |
| **Pine Script Execution** | **Unavailable** | Not supported by Lightweight Charts library primitives; not claimed. |

---

## 6. Verification & Test Results

### 6.1 Backend Integration & Security Tests (129/129 Passed)
Command: `.venv\Scripts\python.exe -m pytest backend/tests`
- **9/9 Gemini Assistant, Indicator & Chart Tests Passed:**
  - `test_alpaca_paper_host_security_allowlist`: rejects `https://api.alpaca.markets` at initialization with `ValueError("SECURITY REJECTION")`.
  - `test_gemini_assistant_unconfigured_status`: verifies graceful status degradation when key is unconfigured.
  - `test_multilingual_language_detection`: tests accurate detection of English (`en`), Hindi (`hi`), and Hinglish (`hi-Latn`).
  - `test_deterministic_technical_indicators_calculation`: checks exact mathematical values and warm-up `None` handling for SMA, EMA, BB, RSI, VWAP.
  - `test_research_request_creates_zero_orders`: ensures research questions never create paper orders.
  - `test_bounded_paper_investment_proposal_and_execution`: validates proposal generation, 10-minute expiry, and explicit user-driven execution.
  - `test_chart_workspace_api_endpoints`: verifies CRUD lifecycle for layouts and time/price drawings.
  - `test_market_history_with_replay_clock`: confirms observations strictly respect `as_of` simulated clock without future lookahead.
  - `test_market_indicators_endpoint`: verifies `/market/indicators/{symbol}` endpoint returns valid series.
- **120/120 Existing Backend Tests Passed:** Zero regressions across auth, risk, alerts, portfolio intelligence, goals, spending, and paper trading ledgers.

### 6.2 Code Quality & Formatting
- `ruff check backend`: 0 errors
- `ruff format backend`: 86 files left cleanly formatted

### 6.3 Web Production Build
Command: `npm run build` in `web/`
- Output: `tsc -b && vite build` succeeded in 1.79s (`dist/index.html`, `dist/assets/index-BMAghMsU.js` 510 kB).

### 6.4 Flutter Mobile Quality
- `flutter analyze`: **No issues found!** (ran in 4.9s)
- `flutter test`: **All tests passed!**

---

## 7. Startup & Run Instructions (Windows PowerShell)

### Prerequisites
- Local PostgreSQL 15+ running on port `5432` with database `finex_db` accessible via pgAdmin.
- Python 3.11+ with virtual environment in `.venv`.
- Node.js 18+ and npm installed.
- Flutter SDK 3.10+ installed.

### Step 1: Database Verification (PostgreSQL & pgAdmin)
Ensure your PostgreSQL server is active. To verify or apply database migrations without touching existing records:
```powershell
# Review generated SQL offline first (transactional DDL):
.venv\Scripts\python.exe -m alembic upgrade head --sql

# Apply new tables (paper_proposals, chart_layouts, chart_drawings, chart_indicator_templates, replay_sessions):
.venv\Scripts\python.exe -m alembic upgrade head
```

### Step 2: Start FastAPI Backend
```powershell
# In root project directory:
.venv\Scripts\python.exe -m uvicorn backend.app.factory:create_app --factory --host 127.0.0.1 --port 8000 --reload
```
Backend Swagger API documentation will be available at: `http://127.0.0.1:8000/docs`

### Step 3: Start React Web Application
```powershell
cd "f:\Project File\Finex Final\web"
npm run dev
```
Open browser at `http://localhost:5173`. Click the **Charts** tab in the top navigation to access the full TradingView-style analytical workspace.

### Step 4: Run Mobile Flutter Application
```powershell
cd "f:\Project File\Finex Final\mobile"
flutter run -d chrome   # Or select an Android emulator / iOS simulator
```
Navigate to **More > TradingView Chart Workspace** or tap any instrument in **Markets** to launch the interactive mobile chart.

---

## 8. Interactive Demonstration Script

### Script A: Indian Historical Replay & Gemini Chart Research
1. Open the **Charts** tab at `http://localhost:5173`.
2. Notice the top status badge reads **`NSE Historical Replay (30D Lag)`** and currency is `₹ (INR)`.
3. Select symbol `RELIANCE` and timeframe `1D`.
4. Toggle `SMA 20` and `BB (20,2)` in the top control bar. Notice the moving averages and volatility bands update on the chart.
5. In the right panel, select **✨ Ask FinEx AI** and enter:
   > *"Is chart ka technical analysis Hindi me samjhao aur moving averages ka kya trend hai?"*
6. The assistant responds in Hindi/Hinglish, referencing the active RELIANCE chart context, price levels, and moving average direction without creating any orders.
7. Next, enter a bounded paper investment command:
   > *"Invest INR 10,000 of my virtual cash across RELIANCE and TCS following moderate risk limits."*
8. The assistant presents a structured **📋 Paper Investment Proposal** with estimated quantities, sub-totals, and an **Execute Paper Proposal** action button.
9. Click **Execute Paper Proposal**. An atomic transaction executes in PostgreSQL:
   - Reserved cash is deducted from `paper_cash_ledger`.
   - Simulated fills are recorded in `paper_trades` with 0.05% brokerage fees.
   - Position markers (Green arrows) appear directly on the RELIANCE chart at the fill price.

### Script B: Paper Order Ticket Execution from Chart Dock
1. In the bottom collapsible panel, click **Paper Order Ticket**.
2. Select side **Paper BUY**, shares **10**, type **Market**.
3. Click **Submit Paper BUY**.
4. An auditory chime sounds, virtual cash balance updates, and the new holding appears instantly in the **Positions** tab.

---

## 9. Known Limitations & Disclaimers

1. **Paper Trading Simulation Only:** All balances, positions, orders, and P&L statements are strictly virtual. No real brokerage connections exist, and live trading permissions are explicitly disallowed.
2. **SEBI Educational Lag:** In accordance with the SEBI 8 May 2026 circular, Indian market data is subject to an educational 30-day delay. Historical replay is intended solely for pedagogical analysis.
3. **LLM Analysis Boundaries:** Gemini responses represent educational analysis grounded in historical price history and regulatory publications. They do not constitute financial advice, equity tips, or guarantees of future market performance.
