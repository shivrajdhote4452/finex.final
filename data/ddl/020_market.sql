-- ==============================================================================
-- FINEX DDL SCHEMA: 020_market.sql
-- Task ID: S3-DAT-01
-- Description: Securities, market quotes, price history, watchlists and items.
-- Developer: Shivraj Dhote (Sole Developer)
-- Baseline Date: 16 October 2026
-- ==============================================================================

-- 1. Securities / Instruments Master Table
CREATE TABLE IF NOT EXISTS securities (
    id UUID PRIMARY KEY,
    symbol VARCHAR(50) NOT NULL,
    exchange VARCHAR(20) NOT NULL DEFAULT 'NSE',
    canonical_id VARCHAR(70) NOT NULL UNIQUE, -- e.g., NSE:RELIANCE
    name VARCHAR(255) NOT NULL,
    sector VARCHAR(100) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'INR',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_securities_symbol_exchange UNIQUE (symbol, exchange)
);

CREATE INDEX IF NOT EXISTS idx_securities_symbol ON securities(symbol);
CREATE INDEX IF NOT EXISTS idx_securities_sector ON securities(sector);

-- 2. Latest Market Quotes Table (with explicit freshness and observation metadata)
CREATE TABLE IF NOT EXISTS market_quotes (
    id UUID PRIMARY KEY,
    security_id UUID NOT NULL REFERENCES securities(id) ON DELETE CASCADE,
    price NUMERIC(18, 4) NOT NULL,
    open_price NUMERIC(18, 4),
    high_price NUMERIC(18, 4),
    low_price NUMERIC(18, 4),
    previous_close NUMERIC(18, 4),
    change NUMERIC(18, 4),
    change_pct NUMERIC(8, 4),
    currency VARCHAR(3) NOT NULL DEFAULT 'INR',
    observed_at TIMESTAMP WITH TIME ZONE NOT NULL,
    ingested_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    source VARCHAR(50) NOT NULL DEFAULT 'yfinance',
    served_from_cache BOOLEAN NOT NULL DEFAULT FALSE,
    is_delayed BOOLEAN NOT NULL DEFAULT FALSE,
    freshness_status VARCHAR(50) NOT NULL DEFAULT 'END_OF_DAY', -- LIVE, END_OF_DAY, DELAYED, STALE
    CONSTRAINT chk_quote_price_positive CHECK (price > 0),
    CONSTRAINT uq_security_quote_observation UNIQUE (security_id, observed_at, source)
);

CREATE INDEX IF NOT EXISTS idx_market_quotes_security ON market_quotes(security_id);
CREATE INDEX IF NOT EXISTS idx_market_quotes_observed_at ON market_quotes(observed_at);

-- 3. Historical Daily OHLCV Price Bars (Unique per security + date + source + adjustment)
CREATE TABLE IF NOT EXISTS market_price_history (
    id UUID PRIMARY KEY,
    security_id UUID NOT NULL REFERENCES securities(id) ON DELETE CASCADE,
    trade_date DATE NOT NULL,
    open_price NUMERIC(18, 4) NOT NULL,
    high_price NUMERIC(18, 4) NOT NULL,
    low_price NUMERIC(18, 4) NOT NULL,
    close_price NUMERIC(18, 4) NOT NULL,
    adj_close_price NUMERIC(18, 4),
    volume BIGINT NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'INR',
    source VARCHAR(50) NOT NULL DEFAULT 'yfinance',
    ingested_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_ohlcv_positive CHECK (open_price > 0 AND high_price > 0 AND low_price > 0 AND close_price > 0),
    CONSTRAINT chk_ohlcv_bounds CHECK (high_price >= low_price AND high_price >= open_price AND high_price >= close_price AND low_price <= open_price AND low_price <= close_price),
    CONSTRAINT chk_volume_non_negative CHECK (volume >= 0),
    CONSTRAINT uq_price_history_natural_key UNIQUE (security_id, trade_date, source)
);

CREATE INDEX IF NOT EXISTS idx_price_history_security_date ON market_price_history(security_id, trade_date DESC);

-- 4. User Watchlists Table
CREATE TABLE IF NOT EXISTS watchlists (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL DEFAULT 'My Watchlist',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_user_watchlist_name UNIQUE (user_id, name)
);

CREATE INDEX IF NOT EXISTS idx_watchlists_user_id ON watchlists(user_id);

-- 5. Watchlist Items Table (User-instrument relationship with duplicate protection)
CREATE TABLE IF NOT EXISTS watchlist_items (
    id UUID PRIMARY KEY,
    watchlist_id UUID NOT NULL REFERENCES watchlists(id) ON DELETE CASCADE,
    security_id UUID NOT NULL REFERENCES securities(id) ON DELETE CASCADE,
    added_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_watchlist_security UNIQUE (watchlist_id, security_id)
);

CREATE INDEX IF NOT EXISTS idx_watchlist_items_watchlist ON watchlist_items(watchlist_id);
