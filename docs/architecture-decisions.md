# FinEx — Architecture & Decision Log (ADR)

**Developer:** Shivraj Dhote  
**Date:** 16 October 2026  
**Status:** Approved  

---

## ADR 001: Separation of Operational and Analytical Storage
- **Context:** The original sprint cards occasionally used "Delta" for mutable operational records (e.g. user accounts, holdings, orders). The Handbook specifies Lakebase/Postgres for operational storage and Databricks Delta for analytical storage.
- **Decision:**
  1. **Operational Database:** PostgreSQL (compatible with Lakebase/Azure Database for PostgreSQL). Handles atomic, user-owned, mutable entities: `users`, `user_profiles`, `user_consents`, `portfolios`, `portfolio_holdings`, `watchlists`, `paper_accounts`, `paper_orders`, `paper_trades`, `paper_positions`, `paper_cash_ledger`, `alert_rules`, `notifications`, `financial_goals`, `transactions`.
  2. **Analytical & History Layer:** Databricks Delta (and local parquet/Delta compatible files during development). Handles immutable snapshots, time-series history, audit copies, application events, evaluation runs, and reconciliation datasets.
  3. **Strict Invariant:** Operational writes (such as paper trade execution, order fills, cash ledger updates) are strictly atomic within PostgreSQL transactions. They NEVER depend on asynchronous analytical updates.

---

## ADR 002: Service Boundaries & Ports/Adapters Architecture
- **Context:** Clean separation of concerns prevents client coupling and vendor lock-in.
- **Flow:**
  `React Web / Flutter Mobile` → `FastAPI (/api/v1)` → `Domain Services` → `Repository & Provider Ports` → `Adapters (Postgres, Delta, Market Providers, LLM, FCM)`
- **Invariants:**
  1. Clients NEVER call databases directly.
  2. Clients NEVER hold cloud or provider secrets.
  3. Domain services are purely deterministic for financial math (risk scoring, portfolio valuation, cash ledger calculations, goal projections). LLMs only explain outputs; they never calculate numbers.

---

## ADR 003: Real-Data Acquisition and Ingestion Policy
- **Context:** Synthetic/random data on real dashboards is strictly forbidden.
- **Policy:**
  1. Use genuine observations (NSE official reports, Yahoo Finance via yfinance adapter, SEBI educational material).
  2. Preserve metadata: source, URL, retrieved_at UTC, observation date, currency, raw/adjusted basis, checksum.
  3. Failure handling: Display last permitted cached record with explicit timestamp, or an honest "Unavailable" status. NEVER convert missing quotes to 0. NEVER fabricate ticks.
  4. Mocks are isolated strictly to automated unit/contract tests and fixture runs.

---

## ADR 004: Frontend Visual Design Authority
- **Directive:** Frontend design is exclusively controlled by Shivraj Dhote.
- **Rules:**
  1. The agent shall NOT independently invent visual layouts, typography, color palettes, animations, or styling for React or Flutter.
  2. Before implementing a screen's visual presentation, the agent requests and awaits Shivraj's screenshots, references, or instructions.
  3. Routine technical implementations (component structure, route guards, API contract bindings, accessibility tags, state handling) proceed cleanly behind approved contracts.
  4. While awaiting visual instructions, work proceeds uninterrupted on backend APIs, databases, real-data pipelines, AI RAG, evaluation, and contracts.

---

## ADR 005: API v1 Envelopes, Error Codes & Correlation IDs
- **Conventions:**
  1. Envelope:
     ```json
     {
       "success": true,
       "data": { ... },
       "meta": { "correlation_id": "...", "timestamp": "...", "version": "v1" }
     }
     ```
  2. Error:
     ```json
     {
       "success": false,
       "error": {
         "code": "ERROR_CODE",
         "message": "Safe human-readable message",
         "details": [ ... ]
       },
       "meta": { "correlation_id": "...", "timestamp": "..." }
     }
     ```
  3. Header `X-Correlation-ID`: Generated or propagated across all requests and logs.


---

## ADR 006: Mobile (Flutter) Scope Decision — Defer vs. Fund
- **Date:** 25 October 2026
- **Status:** DECIDED (DEFER — APPROVED Option A)
- **Decision Record:** [docs/architecture-decisions/adr-006-mobile-app-scope.md](architecture-decisions/adr-006-mobile-app-scope.md)
- **Tradeoff Summary:**
  - **Option A (Defer to post-demo — Adopted):** Focus 100% on web demo stability, zero risk of emulator crashes during presentation, native store packaging in Sprint 9+. Revisit after 10 Nov demo.
  - **Option B (Fund before 31 Oct):** Allocate ~20 hours to Keystore signing and device emulators to demo a live Android APK on 10 Nov.

---

## ADR 007: Delta Lake Analytical Scope Decision — Defer vs. Fund
- **Date:** 25 October 2026
- **Status:** DECIDED (DEFER — APPROVED Option A)
- **Decision Record:** [docs/architecture-decisions/adr-007-delta-lake-scope.md](architecture-decisions/adr-007-delta-lake-scope.md)
- **Tradeoff Summary:**
  - **Option A (Defer to post-demo — Adopted):** Rely on PostgreSQL + local Python runners for demo; 100% deterministic, 0 cloud cluster cost, zero network dropout risk. Revisit after 10 Nov demo.
  - **Option B (Fund before 31 Oct):** Provision live remote Databricks workspace/cluster before 31 Oct; requires cloud budget and adds external service latency risk.
