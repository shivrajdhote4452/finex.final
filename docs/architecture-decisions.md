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

## ADR 006: Mobile (Flutter) Scope Freeze & Deferral Decision
- **Date:** 19 October 2026
- **Status:** Approved (Scope Freeze)
- **Context:** The React + Vite web platform is 100% feature-complete, accessible, verified, and integrated with live market feeds, paper trading, portfolio management, AI chatbot, and responsive live charts. Flutter mobile core screens exist in mobile/lib/, but full native store packaging across Android/iOS requires platform-specific signing keys, emulators, and store review timelines.
- **Decision:** **Defer native mobile release packaging to post-demo (Phase 2 / Sprint 9+).** The web application serves as the primary tier-1 interface for the 10 November 2026 demo handoff. Flutter code remains frozen in the repository as a proven companion client.

---

## ADR 007: Delta Lake Analytical Scope Freeze & Deferral Decision
- **Date:** 19 October 2026
- **Status:** Approved (Scope Freeze)
- **Context:** Operational storage, reconciliation, and audit logs are fully operational in PostgreSQL. Heavy Databricks Delta Lake workflow execution scripts exist in data/ddl/ and workflow_orchestrator.py, but provisioning a live remote Databricks cloud cluster for the single-developer demo adds external network failure risks and cloud cost overhead.
- **Decision:** **Defer live remote Databricks workflow provisioning to post-demo (Phase 2 / Sprint 9+).** For the 10 November 2026 demo, analytical history, price history candles, and portfolio reconciliation are executed deterministically on PostgreSQL and local Python analytical runners, maintaining 100% zero-break reliability without external cluster dependencies.
