# FinEx — Demo Blocker Issues Checklist

> The following 6 issues must be created in GitHub (or tracked manually) under the label `demo-blocker` for the 10 November 2026 demo checkpoint.

---

### Issue 1: `[DEMO-BLOCKER] Enable Branch Protection on main`
- **Labels:** `demo-blocker`
- **Assignee:** `@shivrajdhote4452`
- **Description:**
  CI has quality gates and test suites, but direct git pushes to `main` are currently possible. Protect `main` against accidental untested pushes or forced pushes.
- **Acceptance Criteria:**
  - [ ] GitHub Repo Settings → Branches → Add branch protection rule for `main`.
  - [ ] "Require a pull request before merging" is enabled.
  - [ ] "Require status checks to pass before merging" is enabled (`backend-quality-gates`, `web-quality-gates`).
  - [ ] "Do not allow bypassing the above settings" is enabled.
  - [ ] Direct `git push origin main` from a local commit is rejected by GitHub remote.

---

### Issue 2: `[DEMO-BLOCKER] Gitleaks Secrets Scan for Non-Angel Keys`
- **Labels:** `demo-blocker`
- **Assignee:** `@shivrajdhote4452`
- **Description:**
  Verify that no external credentials (Google AI/Gemini, Alpaca, OAuth client secrets, Database passwords) exist in git history across any branch.
- **Acceptance Criteria:**
  - [ ] Run `gitleaks detect --source . --verbose` with 0 findings.
  - [ ] Run `git log -p --all -S "AIza" -- .` → 0 leaks found.
  - [ ] Run `git log -p --all -S "sk-" -- .` → 0 leaks found.
  - [ ] Any detected historical token is immediately rotated at the provider and purged using `git filter-repo`.

---

### Issue 3: `[DEMO-BLOCKER] Live Angel One Login & Streaming Proof (Wed 21 Oct 09:15–15:30 IST)`
- **Labels:** `demo-blocker`
- **Assignee:** `@shivrajdhote4452`
- **Description:**
  NSE market opens Wednesday 21 October at 09:15 IST (following Tuesday Dussehra). Perform the official market-hours runtime verification of Angel One SmartAPI session generation and tick broadcasting.
- **Acceptance Criteria:**
  - [ ] Backend running with `MARKET_DATA_MODE=INDIAN_LIVE_DATA`.
  - [ ] Backend startup log outputs: `"Angel One SmartAPI authenticated successfully"`.
  - [ ] `get_latest_quote("NSE:RELIANCE")` returns live market-hours LTP.
  - [ ] WebSocket `/api/v1/market/ws/RELIANCE` streams live frames to frontend `FinExLiveChart`.
  - [ ] Capture timestamped log and tick sample in `docs/runbooks/go-live-checklist.md`.

---

### Issue 4: `[DEMO-BLOCKER] Cached-Mode Demo Rehearsal (Diwali Market Closed Scenario)`
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

---

### Issue 5: `[DEMO-BLOCKER] Finalize Mobile & Delta Lake Scope Decisions (ADR 006 & 007)`
- **Labels:** `demo-blocker`
- **Assignee:** `@shivrajdhote4452`
- **Description:**
  Review draft ADRs for Flutter mobile native store packaging and remote Databricks Delta Lake cloud cluster provisioning. Decide whether to defer to post-demo or fund before 31 October 2026.
- **Acceptance Criteria:**
  - [ ] Review [ADR 006: Mobile (Flutter) Scope Decision](architecture-decisions/adr-006-mobile-app-scope.md) and pick Option A (Defer) or Option B (Fund).
  - [ ] Review [ADR 007: Delta Lake Analytical Scope Decision](architecture-decisions/adr-007-delta-lake-scope.md) and pick Option A (Defer) or Option B (Fund).
  - [ ] Update ADR status from `DRAFT` to `APPROVED` on or before 31 October 2026.
  - [ ] Update `docs/task-matrix.md` with final decision links.

---

### Issue 6: `[DEMO-BLOCKER] Clean-Machine Rehearsal Verification`
- **Labels:** `demo-blocker`
- **Assignee:** `@shivrajdhote4452`
- **Description:**
  Execute a clean-machine clone and runbook verification to confirm zero undocumented local dependencies or "works on my machine" issues.
- **Acceptance Criteria:**
  - [ ] Fresh git clone in a clean environment.
  - [ ] `pip install -r backend/requirements.lock` installs cleanly.
  - [ ] `alembic upgrade head` runs cleanly on empty PostgreSQL instance.
  - [ ] `npm ci` and `npm run build` in `web/` complete with 0 errors.
  - [ ] `pytest -m "not live" backend/tests` passes 100%.
  - [ ] Vertical slice verification (Search → Chart → Paper Order → Portfolio) succeeds.
  - [ ] Console execution log saved to `docs/clean_machine_rehearsal.log` and committed.
