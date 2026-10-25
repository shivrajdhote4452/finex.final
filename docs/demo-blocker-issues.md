# FinEx — Demo Blocker Issues Checklist

> Checkpoint audit: 25 October 2026.  
> Status Summary: **3 OPEN / 2 DONE / 1 STALE (SUPERSEDED)** ahead of the 10 November 2026 demo handoff.

---

## Genuinely Open Issues (3)

### Issue 1: `[DEMO-BLOCKER] Enable Branch Protection on main`
- **Status:** **OPEN**
- **Labels:** `demo-blocker`
- **Assignee:** `@shivrajdhote4452`
- **Body Reference:** [docs/issues/issue-1-branch-protection.md](issues/issue-1-branch-protection.md)
- **Description:**
  CI has quality gates and test suites, but direct git pushes to `main` are currently possible. Protect `main` against accidental untested pushes or forced pushes.
- **Acceptance Criteria:**
  - [ ] GitHub Repo Settings → Branches → Add branch protection rule for `main`.
  - [ ] "Require a pull request before merging" is enabled.
  - [ ] "Require status checks to pass before merging" is enabled (`backend-quality-gates`, `web-quality-gates`).
  - [ ] "Do not allow bypassing the above settings" is enabled.
  - [ ] Direct `git push origin main` from a local commit is rejected by GitHub remote.

---

### Issue 4: `[DEMO-BLOCKER] Cached-Mode Demo Rehearsal (Diwali Market Closed Scenario)`
- **Status:** **OPEN**
- **Labels:** `demo-blocker`
- **Assignee:** `@shivrajdhote4452`
- **Body Reference:** [docs/issues/issue-4-cached-mode-rehearsal.md](issues/issue-4-cached-mode-rehearsal.md)
- **Description:**
  Demo day Tuesday 10 November 2026 is Diwali–Balipratipada (NSE closed). Rehearse full presentation in cached mode to guarantee no dead screens, honest timestamp labeling, and zero fake-live numbers.
- **Acceptance Criteria:**
  - [ ] Start backend with `MARKET_DATA_MODE=HISTORICAL_PLAYBACK` (or disconnected external network).
  - [ ] Web UI displays cached candles with genuine historical timestamps.
  - [ ] Top bar and chart badges visibly display `CACHED` / `MARKET CLOSED` state indicators.
  - [ ] Paper trading order placement, ledger accounting, and portfolio analytics function deterministically offline.
  - [ ] Screenshot degraded state banner and save to `docs/runbooks/`.

---

### Issue 6: `[DEMO-BLOCKER] Clean-Machine Rehearsal Verification`
- **Status:** **OPEN**
- **Labels:** `demo-blocker`
- **Assignee:** `@shivrajdhote4452`
- **Body Reference:** [docs/issues/issue-6-clean-machine-rehearsal.md](issues/issue-6-clean-machine-rehearsal.md)
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

---

## Resolved / Closed Issues (2)

### Issue 2: `[DEMO-BLOCKER] Gitleaks Secrets Scan for Non-Angel Keys`
- **Status:** **DONE** (Resolved in [Pull Request #20](https://github.com/shivrajdhote4452/finex.final/pull/20) — merged 25 Oct 2026)
- **Resolution:** Published [docs/secrets-scan-report.md](secrets-scan-report.md) documenting Gitleaks v8.30.1 audit across 104 commits. Verified clean with zero real non-Angel secrets in working tree or git history, and confirmed `.env` has never been committed.

---

### Issue 5: `[DEMO-BLOCKER] Finalize Mobile & Delta Lake Scope Decisions (ADR 006 & 007)`
- **Status:** **DONE** (Resolved in [Pull Request #19](https://github.com/shivrajdhote4452/finex.final/pull/19) — merged 25 Oct 2026)
- **Resolution:** Formally recorded owner decisions as `DECIDED (DEFER)` in [ADR 006](architecture-decisions/adr-006-mobile-app-scope.md) and [ADR 007](architecture-decisions/adr-007-delta-lake-scope.md), deferring mobile and Delta Lake work to post-demo (revisit after 10 Nov demo) to protect demo stability.

---

## Stale / Superseded Issues (1)

### Issue 3: `[DEMO-BLOCKER] Live Angel One Login & Streaming Proof (Wed 21 Oct 09:15–15:30 IST)`
- **Status:** **STALE / SUPERSEDED** (Do NOT create)
- **Reason:** Its market-hours verification window has passed, and demo strategy has pivoted to honest cached/replay mode (Trade Time Machine, [PR #15](https://github.com/shivrajdhote4452/finex.final/pull/15)) for the 10 November Diwali market holiday.
