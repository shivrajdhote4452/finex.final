# FinEx — Data Naming Conventions & Schema Catalog

**Version:** 1.0  
**Scope:** PostgreSQL Operational Storage & Databricks Delta Analytical Catalog  

---

## 1. Naming Rules

1. **Tables & Views:** `snake_case`, pluralized (e.g., `users`, `portfolios`, `market_quotes`).
2. **Primary Keys:** `id` UUID v4 default (or canonical string ID for instruments e.g., `NSE:RELIANCE`).
3. **Foreign Keys:** `<singular_entity>_id` (e.g., `user_id`, `portfolio_id`).
4. **Timestamps:**
   - Always in UTC.
   - Suffix with `_at` (e.g., `created_at`, `updated_at`, `observed_at`, `ingested_at`, `executed_at`).
5. **Monetary Values & Quantities:**
   - Use `NUMERIC(18, 4)` or `NUMERIC(18, 2)` for prices, balances, and values.
   - Use `NUMERIC(18, 6)` for share/crypto quantities.
   - Always accompany monetary values with `currency` (ISO 4217 code, default `'INR'`).
6. **Booleans:** Prefix with `is_` or `has_` (e.g., `is_active`, `has_accepted`).

---

## 2. Catalog & Schema Namespaces

### Operational (PostgreSQL / Lakebase)
- Default schema: `finex_core` (or `public`)
- Core Entities:
  - `users`
  - `user_profiles`
  - `user_preferences`
  - `user_consents`
  - `auth_audit_events`
  - `portfolios`
  - `portfolio_holdings`
  - `watchlists`
  - `watchlist_items`
  - `paper_accounts`
  - `paper_orders`
  - `paper_trades`
  - `paper_positions`
  - `paper_cash_ledger`
  - `alert_rules`
  - `notifications`
  - `financial_goals`
  - `goal_contributions`
  - `transactions`

### Analytical & Events (Databricks Delta)
- Catalog: `finex_analytics`
- Schemas: `dev`, `staging`, `prod`
- Tables:
  - `application_events`
  - `market_price_history`
  - `portfolio_snapshots`
  - `paper_portfolio_snapshots`
  - `monthly_spending_summaries`
  - `ai_evaluation_results`
  - `document_chunks`
