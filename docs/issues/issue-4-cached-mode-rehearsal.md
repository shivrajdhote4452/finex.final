[DEMO-BLOCKER] Cached-Mode Demo Rehearsal (Diwali Market Closed Scenario)

- **Labels:** `demo-blocker`
- **Assignee:** `@shivrajdhote4452`
- **Description:**
  Demo day Tuesday 10 November 2026 is Diwali–Balipratipada (NSE closed). Rehearse full presentation in cached mode to guarantee no dead screens, honest timestamp labeling, and zero fake-live numbers.
- **Acceptance Criteria:**
  - [ ] Start backend with `MARKET_DATA_MODE=HISTORICAL_PLAYBACK` (or disconnected external network).
  - [ ] Web UI displays cached candles with genuine historical timestamps.
  - [ ] Top bar and chart badges visibly display `CACHED` / `MARKET CLOSED` state indicators.
  - [ ] Paper trading order placement, ledger accounting, and portfolio analytics function deterministically offline.
  - [ ] Screenshot degraded state banner and save to `docs/runbooks/`.
