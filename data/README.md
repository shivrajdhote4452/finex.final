# FinEx Database Engineering & Data Assets Guide

**Owner:** Shivraj Dhote (`shivraj.dhote@finex.internal`)  
**Target Platform:** PostgreSQL 15+ / Lakebase / Databricks Delta Lake  
**Database Name:** `finex_db`

---

## 1. Quick Database Setup in pgAdmin 4

If you are using **pgAdmin 4** or standard PostgreSQL on your local machine:

1. **Open pgAdmin 4** and connect to your local PostgreSQL server (`127.0.0.1:5432`).
2. **Create the Database:** Right-click **Databases** -> **Create** -> **Database...** -> Name it `finex_db`.
3. **Open the Query Tool:** Right-click `finex_db` -> Select **Query Tool**.
4. **Open and Run the SQL File:**
   - Click the Open folder icon in pgAdmin.
   - Select [`data/init_finex_db.sql`](./init_finex_db.sql).
   - Click **Execute / Run (F5)**.
5. **Verify:** Expand `finex_db` -> `Schemas` -> `public` -> `Tables`. You will see all 35 tables created with constraints, indexes, and initial seed users/categories/instruments ready!

---

## 2. Initializing via Command Line (`psql` or Alembic)

### Option A: Using `psql`
```bash
psql -U postgres -h 127.0.0.1 -p 5432 -d finex_db -f data/init_finex_db.sql
```

### Option B: Using Alembic Migrations
```bash
# Run all forward migrations to latest head revision
alembic upgrade head
```

---

## 3. Directory Layout

- **[`init_finex_db.sql`](./init_finex_db.sql)**: The complete standalone schema and seed data SQL script. Idempotent (`IF NOT EXISTS`, `ON CONFLICT DO NOTHING`).
- **[`ddl/`](./ddl/)**: Modular domain-specific DDL specifications:
  - `001_core.sql`: User identities, profiles, consent, audit logs.
  - `020_market.sql`: Securities, quotes, observations, daily OHLC.
  - `030_ai_rag.sql`: Regulatory document knowledge base and chat logs.
  - `040_paper_trading.sql`: Virtual trading accounts, orders, positions, and ledger.
  - `050_alerts.sql`: Price and technical alert rules and notifications.
  - `060_goals.sql`: Goal planner, contributions, and projections.
  - `061_spending.sql`: Spending tracker, CSV upload hashes, transaction deduplication.
- **[`access_control/`](./access_control/)**: Unity Catalog and PostgreSQL least-privilege role definitions.
- **[`quality/`](./quality/)**: Automated reconciliation and data hygiene scripts.
- **[`workflows/`](./workflows/)**: Databricks production workflow definitions.

---

## 4. Why `data/local_pg/` is Not Tracked in Git

In your local project folder, `data/local_pg/` is a raw, platform-specific PostgreSQL binary data cluster (containing active process logs, WAL files, heap pages, and lock files). 

Raw database engine data clusters are excluded from GitHub via `.gitignore` (`data/local_pg/`) because:
1. They are tied to a specific operating system, platform architecture, and PostgreSQL version (e.g. Windows x86_64 binaries cannot run on Linux servers, CI/CD runners, or other developers' machines).
2. Live database engine lock files (`postmaster.pid`) and active WAL logs cause corruption when cloned or synced.
3. They bloat repositories beyond GitHub's 100MB file limit.

Instead, database architecture is tracked through clean, portable SQL DDL scripts (`data/init_finex_db.sql`), Alembic migration histories (`alembic/versions/`), and seed data.
