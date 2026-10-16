# FinEx — 96-Task Implementation & Traceability Matrix

**Project:** FinEx (Financial Excellence)  
**Developer:** Shivraj Dhote (Sole Developer)  
**Baseline Date:** 16 October 2026  
**Demonstration Checkpoint:** 10 November 2026  

---

## Status Classification Legend
- **Verified Working**: Implemented with passing executable tests and documented evidence.
- **In Progress**: Active implementation underway.
- **Partially Implemented**: Partial functionality exists; consumers or edge cases pending.
- **Missing / Backlog**: Not yet implemented.
- **Blocked**: Blocked by external credential, paid service, or missing business decision.
- **Deferred**: Post-checkpoint scope.

---

## Week 0 — Enablement & Bootstrap

| Task ID | Component | Description | Status | Evidence / Notes |
|---|---|---|---|---|
| W0-KHY / W0-NIL | Web (React) | Route/design shell, reusable UI kit structure | Verified Working | Implemented per Visual Design Book in `web/` |
| W0-SHI / W0-LIK | Mobile (Flutter) | Flutter flavors, navigation skeleton, theme | Ready | Design Book specifications captured |
| W0-DIS | Backend (FastAPI) | App factory, health/readiness, safe errors | Verified Working | `backend/app/factory.py`, passing tests |
| W0-NAY | Architecture | Ports for LLM, retrieval, market, operational/analytics storage | Verified Working | `backend/app/ports/` |
| W0-PAL | Storage (Postgres) | Postgres connection, migration baseline, transaction proof | Ready | SQLAlchemy + Alembic setup |
| W0-MIT | Analytics (Delta) | Databricks bundle/schema/job skeleton & Delta write proof | Ready | Local fixture / adapter path |
| W0-PIY | Contracts | OpenAPI validation, TS/Dart generation workflow | Ready | Frozen OpenAPI schema tooling |
| W0-PAY / W0-PRA / W0-MRU | AI / ML | Structured validation, policy/prompt registry, mock adapter | Verified Working | `ai/evaluation/evaluate.py` 100% pass |
| W0-SYO | Quality & UAT | Glossary, task/acceptance templates, dependency tracking | Verified Working | Established in docs & matrix |

---

## Sprint 1 — Platform Foundation

| Task ID | Track | Title & Description | Status | Evidence / Output |
|---|---|---|---|---|
| S1-PRD-01 | PRD | React application shell (routes /login, /onboarding, /dashboard, etc.) | Verified Working | Implemented per Visual Design Book in `web/` |
| S1-PRD-02 | PRD | Flutter application shell (dev/staging/prod flavors, routes, widgets) | Backlog | Visual design held per Shivraj's directive |
| S1-PRD-03 | PRD | Cross-platform UI contract (docs/ui-contract-v1.md, state tables, mock JSON) | In Progress | Drafted in `docs/ui-contract-v1.md` |
| S1-API-01 | API | FastAPI factory, /api/v1/health/live, /ready, config loader, env validation | In Progress | `backend/app/factory.py`, `config.py` |
| S1-API-02 | API | API v1 conventions: response envelope, ApiError, correlation ID, middleware | In Progress | `backend/app/core/`, `docs/api-standard-v1.md` |
| S1-API-03 | API | Backend quality gates: Ruff, type checking, pytest coverage, auth stub | In Progress | `pyproject.toml`, test suite |
| S1-DAT-01 | DAT | Databricks catalog/schema design, DDL data/ddl/001_core.sql, naming doc | Ready | `data/ddl/001_core.sql`, `docs/data-naming.md` |
| S1-DAT-02 | DAT | Tables for users, user_profiles, portfolios, holdings, application_events | Ready | Operational Postgres models + DDL |
| S1-DAT-03 | DAT | Core data quality checks (non-null IDs, timestamps, unique emails, positive qty) | Ready | Injected bad row tests |
| S1-AI-01 | AI | AI answer policy specification (docs/ai-answer-policy-v1.md, 30-prompt dataset) | Ready | Policy doc & evaluation dataset |
| S1-AI-02 | AI | RAG experiment notebook & ingestion pipeline with 3 approved documents | Ready | `ai/rag/` pipeline |
| S1-AI-03 | AI | AI evaluation harness v0 (exact match, keywords, citation, disclaimer checks) | Ready | `ai/evaluation/evaluate.py` |

---

## Sprint 2 — Identity, Onboarding and Risk Profile

| Task ID | Track | Title & Description | Status |
|---|---|---|---|
| S2-PRD-01 | PRD | React login, consent, onboarding and risk questionnaire screens | Backlog |
| S2-PRD-02 | PRD | Flutter login, consent, onboarding and risk questionnaire flow | Backlog |
| S2-PRD-03 | PRD | Cross-platform onboarding test automation and analytics events | Backlog |
| S2-API-01 | API | Google OAuth callback, JWT lifecycle, refresh/logout, /users/me | Backlog |
| S2-API-02 | API | Onboarding & consent endpoints, /risk/questions, /risk/assessments | Backlog |
| S2-API-03 | API | Contract and integration tests for auth, profile, consent and risk | Backlog |
| S2-DAT-01 | DAT | Tables users, user_profiles, user_preferences, user_consents, auth_audit_events | Backlog |
| S2-DAT-02 | DAT | Versioned risk_questionnaires, questions, assessments, answers tables & loader | Backlog |
| S2-DAT-03 | DAT | Identity/risk data quality checks and audit query | Backlog |
| S2-AI-01 | AI | Deterministic risk scoring v1 (willingness/capacity, conservative/moderate/aggressive) | Backlog |
| S2-AI-02 | AI | Risk explanation prompt/template (beginner language, citations, limitations) | Backlog |
| S2-AI-03 | AI | Risk evaluation harness extension (score consistency, factor coverage, safety) | Backlog |

---

## Sprint 3 — Market Data, Watchlist and Portfolio

| Task ID | Track | Title & Description | Status |
|---|---|---|---|
| S3-PRD-01 | PRD | React market search, watchlist and portfolio dashboard | Backlog |
| S3-PRD-02 | PRD | Flutter market search, watchlist and portfolio dashboard | Backlog |
| S3-PRD-03 | PRD | Accessible chart wrappers, response mapping and E2E watchlist/portfolio tests | Backlog |
| S3-API-01 | API | /market/search, /market/quotes/{symbol}, watchlists CRUD with freshness | Backlog |
| S3-API-02 | API | Portfolio CRUD, holdings validation, deterministic snapshot calculation | Backlog |
| S3-API-03 | API | Caching, pagination, provider error mapping and contract tests | Backlog |
| S3-DAT-01 | DAT | Securities, market_quotes, market_price_history, watchlists tables | Backlog |
| S3-DAT-02 | DAT | Market data ingestion pipeline, normalization, deduplication & MERGE | Backlog |
| S3-DAT-03 | DAT | Market freshness & portfolio DQ checks (stale quote, orphan item, allocation sum) | Backlog |
| S3-AI-01 | AI | Structured company/fund comparison prompt & schema | Backlog |
| S3-AI-02 | AI | Portfolio explanation tool using deterministic backend metrics | Backlog |
| S3-AI-03 | AI | Factuality/evaluation set for comparisons and portfolio explanations | Backlog |

---

## Sprint 4 — AI Financial Assistant and RAG

| Task ID | Track | Title & Description | Status |
|---|---|---|---|
| S4-PRD-01 | PRD | React AI chat: conversation list, composer, citations, feedback, delete | Backlog |
| S4-PRD-02 | PRD | Flutter AI chat with history, citations, feedback, session expiry | Backlog |
| S4-PRD-03 | PRD | Cross-platform chat test suite and privacy analytics | Backlog |
| S4-API-01 | API | Conversation, message, feedback endpoints with user isolation & pagination | Backlog |
| S4-API-02 | API | AI orchestration service: classification, retrieval, model call, guardrails | Backlog |
| S4-API-03 | API | Feedback endpoint, correlation tracing across API/retrieval/model calls | Backlog |
| S4-DAT-01 | DAT | document_registry, chunks, ai_conversations, messages, feedback, retrieval_events | Backlog |
| S4-DAT-02 | DAT | Vector Search index and retrieval workflow with metadata filters | Backlog |
| S4-DAT-03 | DAT | AI data lineage and quality checks | Backlog |
| S4-AI-01 | AI | Document ingestion pipeline for approved filings/factsheets | Backlog |
| S4-AI-02 | AI | Retrieval evaluation measuring recall@k, metadata filters, stale exclusion | Backlog |
| S4-AI-03 | AI | Answer guardrails and citation validator (unsupported claim blocker) | Backlog |

---

## Sprint 5 — Paper Trading

| Task ID | Track | Title & Description | Status |
|---|---|---|---|
| S5-PRD-01 | PRD | React paper-trading screens: account summary, order ticket, positions, history | Backlog |
| S5-PRD-02 | PRD | Flutter paper-trading account, order ticket, positions and history | Backlog |
| S5-PRD-03 | PRD | Paper-trading E2E and reconciliation tests | Backlog |
| S5-API-01 | API | Paper account CRUD/reset, order submit/list/get, positions with idempotency | Backlog |
| S5-API-02 | API | Deterministic execution/ledger service for buy/sell (atomic transaction) | Backlog |
| S5-API-03 | API | Security, concurrency and failure tests (double submit, rollback) | Backlog |
| S5-DAT-01 | DAT | paper_accounts, orders, trades, positions, cash_ledger, snapshots tables | Backlog |
| S5-DAT-02 | DAT | Snapshot workflow and deterministic equity, cost basis, realized/unrealized P&L | Backlog |
| S5-DAT-03 | DAT | Reconciliation notebook comparing orders, trades, ledger and break report | Backlog |
| S5-AI-01 | AI | Paper-trading coach prompt (order outcome, portfolio impact, learning points) | Backlog |
| S5-AI-02 | AI | Performance narrative pipeline using deterministic paper metrics | Backlog |
| S5-AI-03 | AI | Safety and factuality evaluation for paper-trading coaching | Backlog |

---

## Sprint 6 — Smart Alerts and Conversational Portfolio Intelligence

| Task ID | Track | Title & Description | Status |
|---|---|---|---|
| S6-PRD-01 | PRD | React alert management, notification center and portfolio conversation | Backlog |
| S6-PRD-02 | PRD | Flutter alert management, notification center and portfolio conversation | Backlog |
| S6-PRD-03 | PRD | Cross-platform E2E tests for alert creation/trigger/read and numbers check | Backlog |
| S6-API-01 | API | Alert rule CRUD and evaluation endpoints (price, movement, concentration, risk) | Backlog |
| S6-API-02 | API | Deterministic portfolio intelligence service (allocation, concentration, scenario) | Backlog |
| S6-API-03 | API | Notifications list/read/mark-all endpoints and delivery status tracking | Backlog |
| S6-DAT-01 | DAT | alert_rules, alert_events, notifications, delivery_attempts tables | Backlog |
| S6-DAT-02 | DAT | Portfolio snapshot/metrics pipeline (sector exposure, concentration score) | Backlog |
| S6-DAT-03 | DAT | Alert evaluation job and monitoring queries for due rules, duplicate suppression | Backlog |
| S6-AI-01 | AI | Portfolio-question intent router for holdings, allocation, scenario, fallback | Backlog |
| S6-AI-02 | AI | Conversational portfolio explanation prompt/tool chain | Backlog |
| S6-AI-03 | AI | Scenario/risk evaluation set (concentration, 15% shock, missing price) | Backlog |

---

## Sprint 7 — Goals and Spending Trend Analysis

| Task ID | Track | Title & Description | Status |
|---|---|---|---|
| S7-PRD-01 | PRD | React goal creation/projection/progress & spending CSV dashboard screens | Backlog |
| S7-PRD-02 | PRD | Flutter goal and spending screens with file picker abstraction | Backlog |
| S7-PRD-03 | PRD | Cross-platform upload/projection tests, accessible chart text summaries | Backlog |
| S7-API-01 | API | Goal CRUD, projection and progress endpoints (deterministic formula) | Backlog |
| S7-API-02 | API | Transaction CSV upload, validation, masked storage, category review | Backlog |
| S7-API-03 | API | Privacy, authorization and integration tests for goals/spending | Backlog |
| S7-DAT-01 | DAT | financial_goals, goal_contributions, goal_projections tables | Backlog |
| S7-DAT-02 | DAT | transaction_uploads, transactions, categories, spending_summaries tables | Backlog |
| S7-DAT-03 | DAT | Goal/spending DQ and analytics checks (totals, duplicate transactions) | Backlog |
| S7-AI-01 | AI | Goal-planning explanation tool (projection, shortfall, assumptions) | Backlog |
| S7-AI-02 | AI | Transaction categorization v1 (rules + ML/LLM fallback on masked text) | Backlog |
| S7-AI-03 | AI | Spending trend and anomaly evaluation (recurring, MoM change, unusual) | Backlog |

---

## Sprint 8 — Production Hardening and Release

| Task ID | Track | Title & Description | Status |
|---|---|---|---|
| S8-PRD-01 | PRD | Harden React application: accessibility, bundle size, error monitoring | Backlog |
| S8-PRD-02 | PRD | Harden Flutter application: secure storage, Android release, store packet | Backlog |
| S8-PRD-03 | PRD | Cross-platform UAT fixes, shared copy/validation, user help & limitations | Backlog |
| S8-API-01 | API | Harden FastAPI security: rate limits, CORS, token revocation, secure headers | Backlog |
| S8-API-02 | API | Observability and deployment: structured logs, metrics, health dependencies | Backlog |
| S8-API-03 | API | API integration/load/reliability tests (p95/timeout verification) | Backlog |
| S8-DAT-01 | DAT | Unity Catalog permissions & environment separation for data schemas | Backlog |
| S8-DAT-02 | DAT | Orchestrate production Databricks workflows with retries and monitoring | Backlog |
| S8-DAT-03 | DAT | Final data reconciliation, retention, backup/export and deletion verification | Backlog |
| S8-AI-01 | AI | Full AI regression across all 8 domains (education, risk, RAG, paper, etc.) | Backlog |
| S8-AI-02 | AI | Register AI experiments/prompts in MLflow, version tags, telemetry queries | Backlog |
| S8-AI-03 | AI | Red-team tests for prompt injection, advice, stale data, cross-user privacy | Backlog |

---

## Summary Counts
- **Total Sprint Tasks:** 96 (12 per sprint × 8 sprints)
- **Week 0 Tasks:** 9 bootstrap functional groups
- **Owner:** Shivraj Dhote (Sole Developer)
- **Verified Working:** 0 / 96 (Baseline audit completed, implementation commencing)
