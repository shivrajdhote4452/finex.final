-- FinEx Sprint 5: Paper Trading & Virtual Ledger Schema
-- Task ID: S5-DAT-01
-- Author: Shivraj Dhote
-- Date: 16 October 2026

CREATE TABLE IF NOT EXISTS paper_accounts (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    initial_balance NUMERIC(14, 2) NOT NULL DEFAULT 100000.00, -- ₹1,00,000 initial virtual cash
    current_cash NUMERIC(14, 2) NOT NULL DEFAULT 100000.00,
    currency VARCHAR(10) NOT NULL DEFAULT 'INR',
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE', -- 'ACTIVE', 'FROZEN', 'RESET'
    reset_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_paper_account_user UNIQUE (user_id)
);

CREATE TABLE IF NOT EXISTS paper_orders (
    id VARCHAR(64) PRIMARY KEY,
    account_id VARCHAR(64) NOT NULL REFERENCES paper_accounts(id) ON DELETE CASCADE,
    user_id VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL CHECK (side IN ('BUY', 'SELL')),
    order_type VARCHAR(20) NOT NULL DEFAULT 'MARKET' CHECK (order_type IN ('MARKET', 'LIMIT')),
    quantity NUMERIC(14, 4) NOT NULL CHECK (quantity > 0),
    limit_price NUMERIC(14, 2),
    fill_price NUMERIC(14, 2),
    fee NUMERIC(14, 2) NOT NULL DEFAULT 0.00,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'FILLED', 'REJECTED', 'CANCELLED')),
    rejection_reason VARCHAR(255),
    idempotency_key VARCHAR(128) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_paper_order_idempotency UNIQUE (account_id, idempotency_key)
);

CREATE TABLE IF NOT EXISTS paper_trades (
    id VARCHAR(64) PRIMARY KEY,
    order_id VARCHAR(64) NOT NULL REFERENCES paper_orders(id) ON DELETE CASCADE,
    account_id VARCHAR(64) NOT NULL REFERENCES paper_accounts(id) ON DELETE CASCADE,
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL CHECK (side IN ('BUY', 'SELL')),
    quantity NUMERIC(14, 4) NOT NULL CHECK (quantity > 0),
    price NUMERIC(14, 2) NOT NULL CHECK (price > 0),
    gross_value NUMERIC(14, 2) NOT NULL,
    fee NUMERIC(14, 2) NOT NULL DEFAULT 0.00,
    net_value NUMERIC(14, 2) NOT NULL,
    execution_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS paper_positions (
    id VARCHAR(64) PRIMARY KEY,
    account_id VARCHAR(64) NOT NULL REFERENCES paper_accounts(id) ON DELETE CASCADE,
    symbol VARCHAR(20) NOT NULL,
    quantity NUMERIC(14, 4) NOT NULL CHECK (quantity >= 0),
    average_buy_price NUMERIC(14, 2) NOT NULL CHECK (average_buy_price >= 0),
    total_cost_basis NUMERIC(14, 2) NOT NULL CHECK (total_cost_basis >= 0),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_paper_position_symbol UNIQUE (account_id, symbol)
);

CREATE TABLE IF NOT EXISTS paper_cash_ledger (
    id VARCHAR(64) PRIMARY KEY,
    account_id VARCHAR(64) NOT NULL REFERENCES paper_accounts(id) ON DELETE CASCADE,
    entry_type VARCHAR(30) NOT NULL, -- 'INITIAL_CREDIT', 'BUY_DEBIT', 'SELL_CREDIT', 'FEE_DEBIT', 'RESET_ADJUST'
    amount NUMERIC(14, 2) NOT NULL,
    balance_after NUMERIC(14, 2) NOT NULL,
    reference_id VARCHAR(64), -- Order or Trade or Reset UUID
    description VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS paper_portfolio_snapshots (
    id VARCHAR(64) PRIMARY KEY,
    account_id VARCHAR(64) NOT NULL REFERENCES paper_accounts(id) ON DELETE CASCADE,
    total_equity NUMERIC(14, 2) NOT NULL,
    cash_balance NUMERIC(14, 2) NOT NULL,
    positions_market_value NUMERIC(14, 2) NOT NULL,
    unrealized_pnl NUMERIC(14, 2) NOT NULL,
    realized_pnl NUMERIC(14, 2) NOT NULL DEFAULT 0.00,
    snapshot_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_paper_orders_account ON paper_orders(account_id, created_at);
CREATE INDEX IF NOT EXISTS idx_paper_trades_account ON paper_trades(account_id, execution_time);
CREATE INDEX IF NOT EXISTS idx_paper_ledger_account ON paper_cash_ledger(account_id, created_at);
