-- ==============================================================================
-- FINEX PRODUCTION DATA PLATFORM: UNITY CATALOG LEAST-PRIVILEGE ACCESS CONTROL
-- Author: Shivraj Dhote (shivraj.dhote@finex.internal)
-- Task ID: S8-DAT-01
-- Sprint: Sprint 8 - Production Hardening and Release
-- ==============================================================================

-- 1. CATALOG INITIALIZATION & ENVIRONMENT ISOLATION
CREATE CATALOG IF NOT EXISTS finex_prod
  COMMENT 'FinEx Production Catalog with Strict Isolation and Least Privilege';

USE CATALOG finex_prod;

-- 2. SCHEMA SEGREGATION
CREATE SCHEMA IF NOT EXISTS finex_prod.market_data
  COMMENT 'Sourced authentic market Bhavcopy observations, candles, and corporate actions';

CREATE SCHEMA IF NOT EXISTS finex_prod.portfolio_analytics
  COMMENT 'Aggregated investor holdings, historical returns, sector exposures';

CREATE SCHEMA IF NOT EXISTS finex_prod.ai_rag
  COMMENT 'Registered regulatory documents, SEBI filings, chunks, and vector embeddings';

CREATE SCHEMA IF NOT EXISTS finex_prod.paper_trading
  COMMENT 'Simulated orders, executions, mark-to-market snapshots, and coaching feedback';

CREATE SCHEMA IF NOT EXISTS finex_prod.spending_analytics
  COMMENT 'Privacy-masked spending transactions, recurring subscriptions, monthly budgets';

CREATE SCHEMA IF NOT EXISTS finex_prod.audit_compliance
  COMMENT 'Immutable tamper-evident audit logs, user consent, regulatory disclosures';

-- 3. ROLE & PRINCIPAL DEFINITIONS
-- Principle: Web and Mobile client applications NEVER connect to Databricks directly.
-- Client apps only authenticate against FastAPI backend services.

-- Role: finex_backend_service (FastAPI microservice identity)
CREATE ROLE IF NOT EXISTS finex_backend_service;
GRANT USAGE ON CATALOG finex_prod TO finex_backend_service;
GRANT USAGE ON SCHEMA finex_prod.market_data TO finex_backend_service;
GRANT SELECT ON ALL TABLES IN SCHEMA finex_prod.market_data TO finex_backend_service;

GRANT USAGE ON SCHEMA finex_prod.portfolio_analytics TO finex_backend_service;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA finex_prod.portfolio_analytics TO finex_backend_service;

GRANT USAGE ON SCHEMA finex_prod.ai_rag TO finex_backend_service;
GRANT SELECT ON ALL TABLES IN SCHEMA finex_prod.ai_rag TO finex_backend_service;

GRANT USAGE ON SCHEMA finex_prod.paper_trading TO finex_backend_service;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA finex_prod.paper_trading TO finex_backend_service;

GRANT USAGE ON SCHEMA finex_prod.spending_analytics TO finex_backend_service;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA finex_prod.spending_analytics TO finex_backend_service;

-- Role: finex_data_engineer (ETL / Ingestion Pipelines)
CREATE ROLE IF NOT EXISTS finex_data_engineer;
GRANT USAGE ON CATALOG finex_prod TO finex_data_engineer;
GRANT ALL PRIVILEGES ON SCHEMA finex_prod.market_data TO finex_data_engineer;
GRANT ALL PRIVILEGES ON SCHEMA finex_prod.spending_analytics TO finex_data_engineer;
GRANT ALL PRIVILEGES ON SCHEMA finex_prod.paper_trading TO finex_data_engineer;
GRANT ALL PRIVILEGES ON SCHEMA finex_prod.audit_compliance TO finex_data_engineer;

-- Role: finex_ml_engineer (Vector Search, RAG Models, Embeddings)
CREATE ROLE IF NOT EXISTS finex_ml_engineer;
GRANT USAGE ON CATALOG finex_prod TO finex_ml_engineer;
GRANT ALL PRIVILEGES ON SCHEMA finex_prod.ai_rag TO finex_ml_engineer;
GRANT SELECT ON SCHEMA finex_prod.market_data TO finex_ml_engineer;
-- Explicitly DENIED access to spending PII and personal user profile records
REVOKE ALL PRIVILEGES ON SCHEMA finex_prod.audit_compliance FROM finex_ml_engineer;

-- Role: finex_analyst_readonly (Internal educational BI & reporting)
CREATE ROLE IF NOT EXISTS finex_analyst_readonly;
GRANT USAGE ON CATALOG finex_prod TO finex_analyst_readonly;
GRANT USAGE ON SCHEMA finex_prod.market_data TO finex_analyst_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA finex_prod.market_data TO finex_analyst_readonly;
GRANT USAGE ON SCHEMA finex_prod.portfolio_analytics TO finex_analyst_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA finex_prod.portfolio_analytics TO finex_analyst_readonly;
-- Readonly analyst is STRICTLY DENIED write and DDL operations
REVOKE INSERT, UPDATE, DELETE, CREATE, DROP ON ALL TABLES IN SCHEMA finex_prod.portfolio_analytics FROM finex_analyst_readonly;
REVOKE ALL PRIVILEGES ON SCHEMA finex_prod.audit_compliance FROM finex_analyst_readonly;

-- 4. PUBLIC ACCESS RESTRICTIONS
REVOKE ALL PRIVILEGES ON CATALOG finex_prod FROM `account users`;
REVOKE ALL PRIVILEGES ON CATALOG finex_prod FROM PUBLIC;
