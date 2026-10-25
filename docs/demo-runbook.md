# FinEx — Demo-Day Runbook: 10 November 2026

**Event Date:** Tuesday 10 November 2026 (Diwali–Balipratipada — NSE is CLOSED)  
**Presenter & Owner:** Shivraj Dhote (`shivraj.dhote@finex.internal`)  
**Deployment Target:** Production Preview (`https://exfinal.vercel.app` or custom domain)  
**Core Strategy:** Honest Cached & Candle-by-Candle Replay Mode (Zero Fabricated Numbers)  

---

## 1. Pre-Demo Checklist (Night Before & Morning Of)

Complete these four sanity checks before taking the stage:

- [ ] **1. Production Deployment on Latest `main`:**
  - Verify on Vercel Dashboard that the active deployment commit matches latest `main` on GitHub (`shivrajdhote4452/finex.final`).
  - Open `https://exfinal.vercel.app/` in an incognito window to verify clean asset loading without cached stale bundles.
- [ ] **2. Simulation Flag State (`VITE_DEMO_SIMULATION=false`):**
  - Verify that `VITE_DEMO_SIMULATION` is set to `false` (or omitted, default is `false`).
  - *Expected Honest Default:* When market data is unavailable or exchange is closed, the system shows genuine cached candles (`FALLBACK_CACHED`) or an honest `DISCONNECTED` empty state ("No market data available for this symbol").
  - *If intentionally set to `true`:* The chart synthesizer will activate only on empty data and display the prominent red watermark banner: `⚠️ SIMULATED DATA — randomly generated for display only, not market prices`.
- [ ] **3. Virtual Cash Seed:**
  - Verify the wallet displays the seed capital of **₹10,00,000.00** (or clean reset via Settings).
- [ ] **4. CI Status:**
  - Verify on GitHub Actions that all quality gates are 100% green (168 backend unit/API tests, 10 AI tests, 30 AI baseline eval cases, 60% coverage floor).

---

## 2. On-Stage Demo Script (Word-for-Word & Click-by-Click)

Follow this 5-minute linear walkthrough on stage:

### Act 1: The Honest Opening (30 Seconds)
1. **Navigate:** Open the browser to the FinEx Dashboard overview (`https://exfinal.vercel.app/`).
2. **Say:**
   > *"Good morning everyone. Today is Tuesday, November 10th — Diwali–Balipratipada. In India, the National Stock Exchange is closed today for the holiday. In most demo platforms, you would see fake numbers or simulated random walks masquerading as live prices. FinEx is built on zero-fabrication data honesty: when the market is closed, we tell you it's closed."*

### Act 2: Transitioning to the Trade Time Machine (1 Minute)
1. **Click:** In the left sidebar navigation, click on **`Charts`** (takes you to `ChartWorkspaceScreen`).
2. **Click:** In the top chart toolbar, click the amber button: **`⏳ Time Machine Replay`**.
3. **Say:**
   > *"Because the exchange is closed today, we use FinEx's Trade Time Machine. Rather than fabricating fake live ticks, the Time Machine rewinds to a verified historical trading session and replays genuine 5-minute NSE candles bar-by-bar."*

### Act 3: Testing the Holiday Guard & Selecting the Replay Session (1 Minute)
1. **Click:** In the Time Machine date picker, select today's date: **`2026-11-10`**.
2. **Observe:** The chart immediately renders the honest holiday empty state:
   `NSE was closed on this date (Diwali–Balipratipada (Demo Day — Market Closed)). Indian equities markets observe official exchange holidays. No bars are synthesized. Please select an active NSE trading day (e.g., Friday 16 Oct 2026).`
3. **Say:**
   > *"Notice what happens when I select today's date: the platform refuses to generate synthetic prices. It explicitly recognizes the official NSE exchange holiday."*
4. **Click:** In the date picker, switch to the verified trading day: **`2026-10-16`** (Friday 16 Oct 2026). Symbol defaults to **`RELIANCE`**.
5. **Say:**
   > *"Now let's rewind to Friday, October 16th, 2026 — the most recent fully settled trading session."*

### Act 4: Candle-by-Candle Playback & Replay Paper Trading (2 Minutes)
1. **Observe:**
   - Top persistent ribbon displays:
     `REPLAY — RELIANCE — 2026-10-16 — past NSE data, not live`
   - Initial bar `09:15 IST` is loaded on the Lightweight Chart.
2. **Click:** Press **`▶ Play`** (or toggle speed to `4x`).
3. **Observe:** The chart animates forward 5-minute candle by candle. The clock scrubber advances through the trading hours (`09:15`, `09:20`, `09:25`, ...).
4. **Say:**
   > *"As I press Play, verified historical bars stream in chronological sequence. The persistent watermark ribbon clearly states: REPLAY — past NSE data, not live. Evaluators and students can pause, step forward, or adjust speed."*
5. **Click:** Press **`⏸ Pause`** at any bar (e.g. Bar 15, `10:30 IST`).
6. **Click:** In the Replay Trade Desk on the right, set Quantity to `10` and click **`⚡ Replay BUY`**.
7. **Observe:**
   - Trade executes at the exact close price of the paused replay candle.
   - Confirmation toast appears: `REPLAY — RELIANCE — 2026-10-16 — past NSE data, not live: BUY 10 shares @ ₹... Virtual cash updated!`.
   - Virtual cash decrements accurately from ₹10,00,000.
   - Trade appears in the Replay Execution History ledger below.
8. **Click:** Step forward 3 bars using **`⏭ Step`**, then click **`⚡ Replay SELL`** with Quantity `5`.
9. **Say:**
   > *"Every paper order placed in Replay mode is priced strictly against the authentic historical candle close, tagged with `isReplay: true`, and reconciled against our virtual portfolio ledger without touching live order routes."*

### Act 5: Provenance Honesty on Native Charts (30 Seconds)
1. **Click:** In the top chart toolbar, click the green button: **`FinEx Live (Angel One)`**.
2. **Observe:**
   - Because the live exchange is closed today and market feeds return no live candles, `FinExLiveChart` checks client cache.
   - If cached candles are present, the amber ribbon displays: `ℹ️ Last real data: <date time> — market data unavailable, showing last cached candles`, and the status badge displays `FALLBACK_CACHED`.
   - If no cached candles exist, the honest empty state displays: `"No market data available for this symbol"`, status `DISCONNECTED`.
3. **Say:**
   > *"When we return to the Live Chart, you can see our Option B Data Honesty policy in action. Because the market is offline today, it shows FALLBACK_CACHED with the verified historical observation timestamp. Every number on this screen has traceable provenance."*

---

## 3. Fallback Branches & Live Failure Recovery

If any unexpected obstacle occurs during the live presentation, execute these exact recovery steps:

| Failure Scenario | Live Symptom | Presenter Recovery Action | What to Say |
| :--- | :--- | :--- | :--- |
| **Backend Unreachable / Network Drop** | Chart shows disconnected or API calls fail | Stay in `TradeTimeMachine`. If history endpoint fails, show the clean empty state. | *"Our remote cloud endpoint experienced network latency. Because FinEx is built fail-safe, the platform immediately catches the disconnection and protects the student from stale or corrupted quotes."* |
| **Time Machine Date Error** | Empty state shows "No historical candles available" | Click the quick date reset to `2026-10-16` and select `RELIANCE` or `TCS`. | *"Let's jump to the verified baseline session of October 16th, where the complete intraday candle chain is cached."* |
| **Browser Glitch / Stale Session** | UI freeze or unexpected state | Press `Ctrl+F5` (hard refresh), click `Charts` → `⏳ Time Machine Replay`. Takes 5 seconds. | *"Let me refresh the terminal workspace... and we are immediately back in our rewind state."* |
| **Synthesizer Demo Requested** | Evaluator asks "what if you want to simulate random walks?" | Mention that setting `VITE_DEMO_SIMULATION=true` enables the random walk engine, but it is gated behind a permanent red watermark banner across the top. | *"We built an optional random-walk synthesizer behind `VITE_DEMO_SIMULATION`, but per our zero-fabrication principle, it is strictly forbidden from running without a full-width red SIMULATED DATA watermark."* |

---

## 4. What NEVER to Claim on Stage

Violating any of these rules compromises the integrity of the FinEx presentation:

1. **NEVER call replayed data "live":** Always use the terms *"historical replay"*, *"candle-by-candle playback"*, or *"cached observation"*.
2. **NEVER quote a price without pointing out its provenance:** Always highlight the status pill (`REPLAY`, `FALLBACK_CACHED`, `LIVE`, or `DISCONNECTED`).
3. **NEVER claim mobile or Delta Lake are running in production for this demo:** State clearly that per ADR-006 and ADR-007, native mobile app store packaging and remote Databricks cloud compute were formally **DEFERRED** post-demo to guarantee 100% web terminal stability.
4. **NEVER enable the synthesizer without the watermark:** The synthesizer must never run bare.
