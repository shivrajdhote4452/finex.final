-- ============================================================================
-- FinEx Database Schema Baseline: 001_core.sql
-- Task ID: S1-DAT-01 / S1-DAT-02
-- Dialect: PostgreSQL 15+ / Lakebase Compatible
-- ============================================================================

-- Ensure pgcrypto or uuid-ossp extension for UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ----------------------------------------------------------------------------
-- 1. Users Table (Core Identity)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL,
    provider VARCHAR(50) NOT NULL DEFAULT 'google',
    provider_subject VARCHAR(255) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    CONSTRAINT uq_users_provider_subject UNIQUE (provider, provider_subject),
    CONSTRAINT uq_users_email UNIQUE (email)
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- ----------------------------------------------------------------------------
-- 2. User Profiles
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    full_name VARCHAR(255),
    display_name VARCHAR(100),
    country VARCHAR(3) DEFAULT 'IND',
    experience_level VARCHAR(50) DEFAULT 'BEGINNER',
    onboarding_completed BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    CONSTRAINT uq_user_profiles_user_id UNIQUE (user_id)
);

-- ----------------------------------------------------------------------------
-- 3. User Consents (Audit-compliant explicit consent tracking)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_consents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    consent_version VARCHAR(50) NOT NULL,
    terms_accepted BOOLEAN NOT NULL DEFAULT FALSE,
    privacy_accepted BOOLEAN NOT NULL DEFAULT FALSE,
    educational_disclaimer_accepted BOOLEAN NOT NULL DEFAULT FALSE,
    accepted_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    ip_address VARCHAR(45),
    user_agent TEXT,
    CONSTRAINT uq_user_consent_version UNIQUE (user_id, consent_version)
);

CREATE INDEX IF NOT EXISTS idx_user_consents_user_id ON user_consents(user_id);

-- ----------------------------------------------------------------------------
-- 4. Portfolios (User Investment Portfolios)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS portfolios (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL DEFAULT 'My Primary Portfolio',
    description TEXT,
    currency VARCHAR(3) NOT NULL DEFAULT 'INR',
    is_default BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE INDEX IF NOT EXISTS idx_portfolios_user_id ON portfolios(user_id);

-- ----------------------------------------------------------------------------
-- 5. Portfolio Holdings (Individual Asset Holdings)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS portfolio_holdings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    portfolio_id UUID NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    symbol VARCHAR(50) NOT NULL,
    asset_class VARCHAR(50) NOT NULL DEFAULT 'EQUITY',
    quantity NUMERIC(18, 6) NOT NULL CHECK (quantity > 0),
    cost_basis_per_share NUMERIC(18, 4) NOT NULL CHECK (cost_basis_per_share >= 0),
    currency VARCHAR(3) NOT NULL DEFAULT 'INR',
    purchase_date DATE NOT NULL,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    CONSTRAINT uq_portfolio_symbol_purchase UNIQUE (portfolio_id, symbol, purchase_date)
);

CREATE INDEX IF NOT EXISTS idx_holdings_portfolio_id ON portfolio_holdings(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_holdings_symbol ON portfolio_holdings(symbol);

-- ----------------------------------------------------------------------------
-- 6. Application Events (Operational Audit & Lineage Log)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS application_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    event_type VARCHAR(100) NOT NULL,
    correlation_id VARCHAR(100) NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    ip_address VARCHAR(45),
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE INDEX IF NOT EXISTS idx_app_events_user_id ON application_events(user_id);
CREATE INDEX IF NOT EXISTS idx_app_events_type_time ON application_events(event_type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_app_events_correlation ON application_events(correlation_id);
