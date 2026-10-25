# ADR 007: Delta Lake Analytical Scope Decision — Defer vs. Fund

- **Status:** DECIDED (DEFER)
- **Decision:** APPROVED (Option A — Defer to Post-Demo)
- **Decision Date:** 25 October 2026
- **Decision Authority:** Shivraj Dhote (Project Owner & Sole Developer)

---

## Decision Record
**Decision:** **APPROVED (Option A — Defer to Post-Demo)**

**Rationale:**
Operational data, time-series prices, user accounts, and paper trading ledgers are currently managed in PostgreSQL with 100% transaction isolation, zero data breaks, and sub-second performance. Local analytical Python runners (`data/quality/`, `data_retention_and_erasure.py`) and parquet snapshots fully satisfy analytical requirements for the upcoming demo. Provisioning and maintaining a live remote Databricks cloud cluster introduces cloud subscription costs, cold-start latency, and external network dropout liabilities without educational value for the 10 November presentation.

**Revisit Condition:**
Immediately following the 10 November 2026 demonstration handoff.

---

## Context
Operational data, time-series prices, user accounts, and paper trading ledgers are currently managed in PostgreSQL with 100% transaction isolation and zero data breaks. 

Databricks workflow configurations (`databricks_production_workflows.json`), DDL schemas (`data/ddl/`), and local orchestration runners (`workflow_orchestrator.py`) exist in the repository. However, provisioning and connecting to a live, cloud-hosted Databricks Spark cluster has not been funded.

---

## Tradeoff Analysis (Defer vs. Fund)

### Option A: Defer to Post-Demo (Adopted Decision)
- **Tradeoff:**
  - **Pros:** 100% deterministic local execution on PostgreSQL and local Python analytical runners (`data/quality/`, `data_retention_and_erasure.py`). Eliminates cloud cluster idle costs, complex cloud storage credential management, and external cluster network latency/dropouts during the demo.
  - **Cons:** Analytical lakehouse queries run via PostgreSQL and local parquet files rather than live remote Databricks compute.
- **Estimated Effort:** 0 additional hours before 10 November 2026. Databricks remote cloud provisioning scheduled for Sprint 9+ (Phase 2).

### Option B: Fund Before 31 October 2026
- **Tradeoff:**
  - **Pros:** Full live Databricks Unity Catalog and Delta Lake workflows visible in cloud console during demo.
  - **Cons:** Requires active cloud credentials, Databricks workspace subscription costs, cluster spin-up latency (3–5 min cold start), and potential network timeout hazards during presentation.
- **Estimated Effort:** 10–15 hours before 31 October 2026 (Databricks workspace provisioning, cluster policy definition, token setup).

