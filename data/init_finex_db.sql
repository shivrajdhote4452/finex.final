-- ============================================================================
-- FinEx Database Baseline Schema & Initial Seed Data
-- Database Dialect: PostgreSQL 15+ / Lakebase Compatible
-- Target Database: finex_db
-- Owner: Shivraj Dhote (shivraj.dhote@finex.internal)
--
-- Instructions for pgAdmin / psql:
-- 1. Open pgAdmin 4 -> Connect to your PostgreSQL server.
-- 2. Create database 'finex_db' (if not already created).
-- 3. Right-click 'finex_db' -> Select 'Query Tool'.
-- 4. Open and execute this script (F5).
-- 5. All 35 tables, constraints, indexes, and seed records will be created.
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================================
-- 1. CORE AUTHENTICATION & IDENTITY TABLES
-- ============================================================================

CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(64) PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    provider VARCHAR(50) NOT NULL DEFAULT 'google',
    provider_subject VARCHAR(255) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    CONSTRAINT uq_users_provider_subject UNIQUE (provider, provider_subject)
);
CREATE INDEX IF NOT EXISTS ix_users_email ON users(email);

CREATE TABLE IF NOT EXISTS user_profiles (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    full_name VARCHAR(255),
    display_name VARCHAR(100),
    country VARCHAR(3) NOT NULL DEFAULT 'IND',
    experience_level VARCHAR(50) NOT NULL DEFAULT 'BEGINNER',
    onboarding_completed BOOLEAN NOT NULL DEFAULT FALSE,
    risk_band VARCHAR(50) DEFAULT 'MODERATE',
    composite_score NUMERIC(5, 2) DEFAULT 50.00,
    risk_assessment JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE IF NOT EXISTS user_consents (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    consent_version VARCHAR(50) NOT NULL,
    terms_accepted BOOLEAN NOT NULL DEFAULT FALSE,
    privacy_accepted BOOLEAN NOT NULL DEFAULT FALSE,
    educational_disclaimer_accepted BOOLEAN NOT NULL DEFAULT FALSE,
    accepted_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    ip_address VARCHAR(45),
    user_agent TEXT,
    CONSTRAINT uq_user_consent_version UNIQUE (user_id, consent_version)
);
CREATE INDEX IF NOT EXISTS ix_user_consents_user_id ON user_consents(user_id);

CREATE TABLE IF NOT EXISTS user_audit_logs (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(100) NOT NULL,
    entity_id VARCHAR(64),
    payload JSONB,
    ip_address VARCHAR(45),
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX IF NOT EXISTS ix_user_audit_logs_user_id ON user_audit_logs(user_id);

CREATE TABLE IF NOT EXISTS revoked_tokens (
    id VARCHAR(64) PRIMARY KEY,
    token VARCHAR(512) NOT NULL UNIQUE,
    user_id VARCHAR(64) REFERENCES users(id) ON DELETE CASCADE,
    revoked_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX IF NOT EXISTS ix_revoked_tokens_token ON revoked_tokens(token);
CREATE INDEX IF NOT EXISTS ix_revoked_tokens_user_id ON revoked_tokens(user_id);

-- ============================================================================
-- 2. PORTFOLIO & HOLDINGS
-- ============================================================================

CREATE TABLE IF NOT EXISTS portfolios (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL DEFAULT 'My Primary Portfolio',
    description TEXT,
    currency VARCHAR(3) NOT NULL DEFAULT 'INR',
    is_default BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX IF NOT EXISTS ix_portfolios_user_id ON portfolios(user_id);

CREATE TABLE IF NOT EXISTS portfolio_holdings (
    id VARCHAR(64) PRIMARY KEY,
    portfolio_id VARCHAR(64) NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
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
CREATE INDEX IF NOT EXISTS ix_portfolio_holdings_portfolio_id ON portfolio_holdings(portfolio_id);
CREATE INDEX IF NOT EXISTS ix_portfolio_holdings_symbol ON portfolio_holdings(symbol);

-- ============================================================================
-- 3. MARKET DATA, SECURITIES & QUOTES
-- ============================================================================

CREATE TABLE IF NOT EXISTS securities (
    id VARCHAR(64) PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    isin VARCHAR(12) UNIQUE,
    exchange VARCHAR(10) NOT NULL DEFAULT 'NSE',
    currency VARCHAR(3) NOT NULL DEFAULT 'INR',
    asset_class VARCHAR(50) NOT NULL DEFAULT 'EQUITY',
    sector VARCHAR(100),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX IF NOT EXISTS ix_securities_symbol ON securities(symbol);

CREATE TABLE IF NOT EXISTS market_quotes (
    id VARCHAR(64) PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL UNIQUE,
    last_price NUMERIC(14, 2) NOT NULL,
    change_amount NUMERIC(14, 2),
    change_percentage NUMERIC(6, 2),
    open_price NUMERIC(14, 2),
    high_price NUMERIC(14, 2),
    low_price NUMERIC(14, 2),
    volume NUMERIC(18, 0),
    quote_timestamp TIMESTAMPTZ NOT NULL,
    source VARCHAR(50) NOT NULL DEFAULT 'nse_realtime',
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX IF NOT EXISTS ix_market_quotes_symbol ON market_quotes(symbol);

CREATE TABLE IF NOT EXISTS market_price_history (
    id VARCHAR(64) PRIMARY KEY,
    security_id VARCHAR(64) NOT NULL REFERENCES securities(id) ON DELETE CASCADE,
    price_date DATE NOT NULL,
    open_price NUMERIC(14, 2) NOT NULL,
    high_price NUMERIC(14, 2) NOT NULL,
    low_price NUMERIC(14, 2) NOT NULL,
    close_price NUMERIC(14, 2) NOT NULL,
    adjusted_close NUMERIC(14, 2) NOT NULL,
    volume NUMERIC(18, 0) NOT NULL,
    data_source VARCHAR(50) NOT NULL DEFAULT 'nse',
    is_interpolated BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    CONSTRAINT uq_security_price_date UNIQUE (security_id, price_date)
);
CREATE INDEX IF NOT EXISTS ix_market_price_history_security_id ON market_price_history(security_id);
CREATE INDEX IF NOT EXISTS ix_market_price_history_price_date ON market_price_history(price_date);

CREATE TABLE IF NOT EXISTS market_observations (
    id VARCHAR(64) PRIMARY KEY,
    symbol VARCHAR(32) NOT NULL,
    price NUMERIC(14, 2) NOT NULL,
    change_pct NUMERIC(6, 2),
    observation_time TIMESTAMPTZ NOT NULL,
    retrieval_time TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    source VARCHAR(64) NOT NULL,
    source_evidence VARCHAR(128) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX IF NOT EXISTS ix_market_observations_symbol ON market_observations(symbol);
CREATE INDEX IF NOT EXISTS ix_market_observations_observation_time ON market_observations(observation_time);

CREATE TABLE IF NOT EXISTS daily_ohlc (
    id VARCHAR(64) PRIMARY KEY,
    symbol VARCHAR(32) NOT NULL,
    trade_date DATE NOT NULL,
    open_price NUMERIC(14, 2) NOT NULL,
    high_price NUMERIC(14, 2) NOT NULL,
    low_price NUMERIC(14, 2) NOT NULL,
    close_price NUMERIC(14, 2) NOT NULL,
    volume NUMERIC(18, 0) NOT NULL,
    source VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    CONSTRAINT uq_daily_ohlc_symbol_date UNIQUE (symbol, trade_date)
);

CREATE TABLE IF NOT EXISTS index_constituents (
    id VARCHAR(64) PRIMARY KEY,
    index_symbol VARCHAR(32) NOT NULL,
    constituent_symbol VARCHAR(32) NOT NULL,
    weight_pct NUMERIC(6, 4) NOT NULL,
    effective_date DATE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    CONSTRAINT uq_index_constituent UNIQUE (index_symbol, constituent_symbol, effective_date)
);

-- ============================================================================
-- 4. WATCHLISTS, ALERTS & NOTIFICATIONS
-- ============================================================================

CREATE TABLE IF NOT EXISTS watchlists (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    name VARCHAR(100) NOT NULL,
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX IF NOT EXISTS ix_watchlists_user_id ON watchlists(user_id);

CREATE TABLE IF NOT EXISTS watchlist_items (
    id VARCHAR(64) PRIMARY KEY,
    watchlist_id VARCHAR(64) NOT NULL REFERENCES watchlists(id) ON DELETE CASCADE,
    security_id VARCHAR(64) NOT NULL REFERENCES securities(id) ON DELETE CASCADE,
    added_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    CONSTRAINT uq_watchlist_security UNIQUE (watchlist_id, security_id)
);
CREATE INDEX IF NOT EXISTS ix_watchlist_items_watchlist_id ON watchlist_items(watchlist_id);

CREATE TABLE IF NOT EXISTS alert_rules (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    rule_type VARCHAR(32) NOT NULL,
    symbol VARCHAR(16),
    comparison_operator VARCHAR(8) NOT NULL,
    threshold_value NUMERIC(14, 4) NOT NULL,
    threshold_unit VARCHAR(16) NOT NULL,
    cooldown_minutes INTEGER NOT NULL DEFAULT 60,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_triggered_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX IF NOT EXISTS ix_alert_rules_user_id ON alert_rules(user_id);

CREATE TABLE IF NOT EXISTS alert_events (
    id VARCHAR(64) PRIMARY KEY,
    rule_id VARCHAR(64) NOT NULL REFERENCES alert_rules(id) ON DELETE CASCADE,
    user_id VARCHAR(64) NOT NULL,
    event_payload JSONB NOT NULL,
    triggered_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX IF NOT EXISTS ix_alert_events_user_id ON alert_events(user_id);

CREATE TABLE IF NOT EXISTS notifications (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    alert_event_id VARCHAR(64) REFERENCES alert_events(id) ON DELETE SET NULL,
    category VARCHAR(32) NOT NULL,
    title VARCHAR(255) NOT NULL,
    body TEXT NOT NULL,
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    read_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX IF NOT EXISTS ix_notifications_user_id ON notifications(user_id);
CREATE INDEX IF NOT EXISTS ix_notifications_is_read ON notifications(is_read);

-- ============================================================================
-- 5. FINANCIAL GOALS & PROJECTIONS
-- ============================================================================

CREATE TABLE IF NOT EXISTS financial_goals (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    title VARCHAR(128) NOT NULL,
    category VARCHAR(32) NOT NULL,
    target_amount NUMERIC(14, 2) NOT NULL,
    current_amount NUMERIC(14, 2) NOT NULL DEFAULT 0.00,
    currency VARCHAR(8) NOT NULL DEFAULT 'INR',
    target_date DATE NOT NULL,
    assumed_annual_return_pct NUMERIC(5, 2) NOT NULL DEFAULT 8.00,
    status VARCHAR(16) NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX IF NOT EXISTS ix_financial_goals_user_id ON financial_goals(user_id);

CREATE TABLE IF NOT EXISTS goal_contributions (
    id VARCHAR(64) PRIMARY KEY,
    goal_id VARCHAR(64) NOT NULL REFERENCES financial_goals(id) ON DELETE CASCADE,
    user_id VARCHAR(64) NOT NULL,
    amount NUMERIC(14, 2) NOT NULL,
    contribution_date DATE NOT NULL,
    notes VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX IF NOT EXISTS ix_goal_contributions_goal_id ON goal_contributions(goal_id);
CREATE INDEX IF NOT EXISTS ix_goal_contributions_user_id ON goal_contributions(user_id);

CREATE TABLE IF NOT EXISTS goal_projections (
    id VARCHAR(64) PRIMARY KEY,
    goal_id VARCHAR(64) NOT NULL REFERENCES financial_goals(id) ON DELETE CASCADE,
    user_id VARCHAR(64) NOT NULL DEFAULT 'usr-shivraj-001',
    projection_date DATE NOT NULL,
    projected_amount NUMERIC(14, 2) NOT NULL DEFAULT 0.00,
    projected_future_value NUMERIC(14, 2),
    shortfall_surplus NUMERIC(14, 2) NOT NULL DEFAULT 0.00,
    confidence_interval_low NUMERIC(14, 2) NOT NULL DEFAULT 0.00,
    confidence_interval_high NUMERIC(14, 2) NOT NULL DEFAULT 0.00,
    required_monthly_savings NUMERIC(14, 2),
    months_remaining INTEGER,
    formula_version VARCHAR(16) NOT NULL DEFAULT 'v1.0',
    assumptions_version VARCHAR(32),
    assumptions_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    calculated_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX IF NOT EXISTS ix_goal_projections_goal_id ON goal_projections(goal_id);
CREATE INDEX IF NOT EXISTS ix_goal_projections_user_id ON goal_projections(user_id);

-- ============================================================================
-- 6. SPENDING, TRANSACTIONS & CATEGORIES
-- ============================================================================

CREATE TABLE IF NOT EXISTS transaction_categories (
    id VARCHAR(32) PRIMARY KEY,
    name VARCHAR(64) NOT NULL,
    description VARCHAR(255),
    is_essential BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE IF NOT EXISTS transaction_uploads (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_hash_sha256 VARCHAR(64) NOT NULL,
    total_rows INTEGER NOT NULL DEFAULT 0,
    accepted_rows INTEGER NOT NULL DEFAULT 0,
    quarantined_rows INTEGER NOT NULL DEFAULT 0,
    status VARCHAR(16) NOT NULL DEFAULT 'COMMITTED',
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    CONSTRAINT uq_upload_user_file_hash UNIQUE (user_id, file_hash_sha256)
);
CREATE INDEX IF NOT EXISTS ix_transaction_uploads_user_id ON transaction_uploads(user_id);

CREATE TABLE IF NOT EXISTS transactions (
    id VARCHAR(64) PRIMARY KEY,
    upload_id VARCHAR(64) REFERENCES transaction_uploads(id) ON DELETE SET NULL,
    user_id VARCHAR(64) NOT NULL,
    transaction_date DATE NOT NULL,
    amount NUMERIC(14, 2) NOT NULL,
    transaction_type VARCHAR(8) NOT NULL,
    masked_description VARCHAR(255) NOT NULL,
    category_id VARCHAR(32) NOT NULL REFERENCES transaction_categories(id),
    categorization_method VARCHAR(16) NOT NULL DEFAULT 'RULE',
    confidence_score NUMERIC(3, 2) NOT NULL DEFAULT 1.00,
    is_reviewed BOOLEAN NOT NULL DEFAULT FALSE,
    dedupe_hash VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    CONSTRAINT uq_transaction_user_dedupe UNIQUE (user_id, dedupe_hash)
);
CREATE INDEX IF NOT EXISTS ix_transactions_user_id ON transactions(user_id);
CREATE INDEX IF NOT EXISTS ix_transactions_category_id ON transactions(category_id);

CREATE TABLE IF NOT EXISTS monthly_spending_summaries (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    year_month VARCHAR(7) NOT NULL,
    total_debit NUMERIC(14, 2) NOT NULL DEFAULT 0.00,
    total_credit NUMERIC(14, 2) NOT NULL DEFAULT 0.00,
    net_savings NUMERIC(14, 2) NOT NULL DEFAULT 0.00,
    savings_rate_pct NUMERIC(5, 2) NOT NULL DEFAULT 0.00,
    transaction_count INTEGER NOT NULL DEFAULT 0,
    category_breakdown JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    CONSTRAINT uq_user_monthly_summary UNIQUE (user_id, year_month)
);
CREATE INDEX IF NOT EXISTS ix_monthly_spending_summaries_user_id ON monthly_spending_summaries(user_id);

CREATE TABLE IF NOT EXISTS transaction_previews (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_hash_sha256 VARCHAR(64) NOT NULL,
    total_rows INTEGER NOT NULL DEFAULT 0,
    valid_rows JSONB NOT NULL,
    duplicate_rows JSONB NOT NULL,
    invalid_rows JSONB NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    committed_upload_id VARCHAR(64),
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    expires_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_transaction_previews_user_id ON transaction_previews(user_id);
CREATE INDEX IF NOT EXISTS ix_transaction_previews_file_hash ON transaction_previews(file_hash_sha256);

-- ============================================================================
-- 7. PAPER TRADING & VIRTUAL LEDGER
-- ============================================================================

CREATE TABLE IF NOT EXISTS paper_accounts (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    account_number VARCHAR(32) NOT NULL UNIQUE,
    currency VARCHAR(3) NOT NULL DEFAULT 'INR',
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    cash_balance NUMERIC(14, 2) NOT NULL DEFAULT 1000000.00,
    current_cash NUMERIC(14, 2) NOT NULL DEFAULT 1000000.00,
    initial_balance NUMERIC(14, 2) NOT NULL DEFAULT 1000000.00,
    total_realized_pnl NUMERIC(14, 2) NOT NULL DEFAULT 0.00,
    total_trades_count INTEGER NOT NULL DEFAULT 0,
    reset_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE IF NOT EXISTS paper_orders (
    id VARCHAR(64) PRIMARY KEY,
    account_id VARCHAR(64) NOT NULL REFERENCES paper_accounts(id) ON DELETE CASCADE,
    user_id VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL,
    order_type VARCHAR(20) NOT NULL,
    quantity NUMERIC(14, 4) NOT NULL,
    limit_price NUMERIC(14, 2),
    fill_price NUMERIC(14, 2),
    fee NUMERIC(14, 2) NOT NULL DEFAULT 0.00,
    status VARCHAR(20) NOT NULL,
    rejection_reason VARCHAR(255),
    idempotency_key VARCHAR(128) NOT NULL,
    execution_receipt JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    CONSTRAINT uq_paper_order_idempotency UNIQUE (account_id, idempotency_key)
);
CREATE INDEX IF NOT EXISTS ix_paper_orders_account_id ON paper_orders(account_id);
CREATE INDEX IF NOT EXISTS ix_paper_orders_user_id ON paper_orders(user_id);

CREATE TABLE IF NOT EXISTS paper_trades (
    id VARCHAR(64) PRIMARY KEY,
    order_id VARCHAR(64) NOT NULL UNIQUE REFERENCES paper_orders(id) ON DELETE CASCADE,
    account_id VARCHAR(64) NOT NULL REFERENCES paper_accounts(id) ON DELETE CASCADE,
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL,
    quantity NUMERIC(14, 4) NOT NULL,
    price NUMERIC(14, 2) NOT NULL,
    gross_value NUMERIC(14, 2) NOT NULL,
    fee NUMERIC(14, 2) NOT NULL DEFAULT 0.00,
    net_value NUMERIC(14, 2) NOT NULL,
    execution_time TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX IF NOT EXISTS ix_paper_trades_account_id ON paper_trades(account_id);
CREATE INDEX IF NOT EXISTS ix_paper_trades_order_id ON paper_trades(order_id);

CREATE TABLE IF NOT EXISTS paper_execution_receipts (
    id VARCHAR(64) PRIMARY KEY,
    order_id VARCHAR(64) NOT NULL UNIQUE REFERENCES paper_orders(id) ON DELETE CASCADE,
    account_id VARCHAR(64) NOT NULL REFERENCES paper_accounts(id) ON DELETE CASCADE,
    user_id VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL,
    quantity NUMERIC(14, 4) NOT NULL,
    fill_price NUMERIC(14, 2) NOT NULL,
    gross_value NUMERIC(14, 2) NOT NULL,
    fee NUMERIC(14, 2) NOT NULL DEFAULT 0.00,
    net_value NUMERIC(14, 2) NOT NULL,
    executed_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE IF NOT EXISTS paper_positions (
    id VARCHAR(64) PRIMARY KEY,
    account_id VARCHAR(64) NOT NULL REFERENCES paper_accounts(id) ON DELETE CASCADE,
    symbol VARCHAR(20) NOT NULL,
    quantity NUMERIC(14, 4) NOT NULL,
    average_buy_price NUMERIC(14, 2) NOT NULL,
    total_cost_basis NUMERIC(14, 2) NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    CONSTRAINT uq_paper_position_symbol UNIQUE (account_id, symbol)
);

CREATE TABLE IF NOT EXISTS paper_cash_ledger (
    id VARCHAR(64) PRIMARY KEY,
    account_id VARCHAR(64) NOT NULL REFERENCES paper_accounts(id) ON DELETE CASCADE,
    entry_type VARCHAR(30) NOT NULL,
    amount NUMERIC(14, 2) NOT NULL,
    balance_after NUMERIC(14, 2) NOT NULL,
    reference_id VARCHAR(64),
    description VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX IF NOT EXISTS ix_paper_cash_ledger_account_id ON paper_cash_ledger(account_id);

-- ============================================================================
-- 8. AI RAG KNOWLEDGE BASE, CONVERSATIONS & RETRIEVAL LINEAGE
-- ============================================================================

CREATE TABLE IF NOT EXISTS document_registry (
    id VARCHAR(64) PRIMARY KEY,
    document_id VARCHAR(64),
    title VARCHAR(255) NOT NULL,
    doc_type VARCHAR(50) NOT NULL DEFAULT 'REGULATION',
    publisher VARCHAR(128) NOT NULL,
    publishing_date DATE NOT NULL DEFAULT CURRENT_DATE,
    published_date DATE,
    reporting_period VARCHAR(50),
    security_symbol VARCHAR(20),
    isin VARCHAR(20),
    source_url VARCHAR(512),
    content_hash VARCHAR(64) NOT NULL DEFAULT 'sha256-pending',
    content_hash_sha256 VARCHAR(64),
    retrieval_timestamp TIMESTAMPTZ,
    chunk_count INTEGER NOT NULL DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX IF NOT EXISTS ix_document_registry_title ON document_registry(title);

CREATE TABLE IF NOT EXISTS document_chunks (
    id VARCHAR(64) PRIMARY KEY,
    document_id VARCHAR(64) NOT NULL REFERENCES document_registry(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL DEFAULT '',
    chunk_text TEXT,
    section_title VARCHAR(255),
    page_number INTEGER,
    word_count INTEGER NOT NULL DEFAULT 0,
    token_count INTEGER,
    embedding_vector JSONB,
    embedding_vector_id VARCHAR(128),
    metadata JSONB,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    CONSTRAINT uq_doc_chunk UNIQUE (document_id, chunk_index)
);
CREATE INDEX IF NOT EXISTS ix_document_chunks_document_id ON document_chunks(document_id);

CREATE TABLE IF NOT EXISTS ai_conversations (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL DEFAULT 'Financial Research Session',
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX IF NOT EXISTS ix_ai_conversations_user_id ON ai_conversations(user_id);

CREATE TABLE IF NOT EXISTS ai_messages (
    id VARCHAR(64) PRIMARY KEY,
    conversation_id VARCHAR(64) NOT NULL REFERENCES ai_conversations(id) ON DELETE CASCADE,
    user_id VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    intent_detected VARCHAR(50),
    correlation_id VARCHAR(64) NOT NULL,
    latency_ms DOUBLE PRECISION,
    model_version VARCHAR(50),
    is_fallback BOOLEAN DEFAULT FALSE,
    citation_chunk_ids JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX IF NOT EXISTS ix_ai_messages_conversation_id ON ai_messages(conversation_id);
CREATE INDEX IF NOT EXISTS ix_ai_messages_user_id ON ai_messages(user_id);

CREATE TABLE IF NOT EXISTS ai_feedback (
    id VARCHAR(64) PRIMARY KEY,
    message_id VARCHAR(64) NOT NULL REFERENCES ai_messages(id) ON DELETE CASCADE,
    user_id VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    rating INTEGER NOT NULL,
    feedback_type VARCHAR(50),
    comments TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    CONSTRAINT uq_user_message_feedback UNIQUE (user_id, message_id)
);
CREATE INDEX IF NOT EXISTS ix_ai_feedback_message_id ON ai_feedback(message_id);

CREATE TABLE IF NOT EXISTS retrieval_events (
    id VARCHAR(64) PRIMARY KEY,
    correlation_id VARCHAR(64) NOT NULL,
    conversation_id VARCHAR(64),
    query_text TEXT NOT NULL,
    filter_metadata JSONB,
    top_k INTEGER NOT NULL,
    retrieved_chunk_ids JSONB,
    latency_ms DOUBLE PRECISION,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX IF NOT EXISTS ix_retrieval_events_correlation_id ON retrieval_events(correlation_id);

-- Legacy aliases for backwards compatibility
CREATE TABLE IF NOT EXISTS rag_documents (
    id VARCHAR(64) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    source_url VARCHAR(500),
    publisher VARCHAR(100) NOT NULL,
    document_type VARCHAR(50) NOT NULL DEFAULT 'REGULATION',
    version VARCHAR(50),
    publication_date DATE,
    content_hash VARCHAR(64),
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE IF NOT EXISTS rag_chunks (
    id VARCHAR(64) PRIMARY KEY,
    document_id VARCHAR(64) NOT NULL REFERENCES rag_documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    section_title VARCHAR(255),
    page_number INTEGER,
    chunk_text TEXT NOT NULL,
    token_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX IF NOT EXISTS ix_rag_chunks_document_id ON rag_chunks(document_id);

CREATE TABLE IF NOT EXISTS ai_chat_sessions (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL DEFAULT 'Financial Inquiry',
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX IF NOT EXISTS ix_ai_chat_sessions_user_id ON ai_chat_sessions(user_id);

CREATE TABLE IF NOT EXISTS ai_chat_messages (
    id VARCHAR(64) PRIMARY KEY,
    session_id VARCHAR(64) NOT NULL REFERENCES ai_chat_sessions(id) ON DELETE CASCADE,
    sender VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    citations JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX IF NOT EXISTS ix_ai_chat_messages_session_id ON ai_chat_messages(session_id);

-- ============================================================================
-- 9. INITIAL SEED DATA
-- ============================================================================

-- Standard Baseline Transaction Categories
INSERT INTO transaction_categories (id, name, description, is_essential) VALUES
    ('FOOD_DINING', 'Food & Dining', 'Restaurants, cafes, food delivery', FALSE),
    ('GROCERIES', 'Groceries & Essentials', 'Supermarkets, daily groceries, staples', TRUE),
    ('UTILITIES', 'Bills & Utilities', 'Electricity, water, broadband, gas', TRUE),
    ('HOUSING', 'Rent & Housing', 'Home rent, society maintenance', TRUE),
    ('TRAVEL', 'Travel & Transport', 'Fuel, cab rides, transit, flights', FALSE),
    ('SHOPPING', 'Shopping & Lifestyle', 'Clothing, electronics, personal purchases', FALSE),
    ('HEALTHCARE', 'Health & Medical', 'Pharmacies, clinics, medical insurance', TRUE),
    ('INVESTMENTS', 'Savings & Investments', 'SIPs, mutual funds, equity purchases', FALSE),
    ('INCOME', 'Income & Salary', 'Payroll, dividends, consulting receipts', FALSE),
    ('OTHER', 'General & Unclassified', 'Miscellaneous expense items', FALSE)
ON CONFLICT (id) DO NOTHING;

-- Default Principal User (Shivraj Dhote)
INSERT INTO users (id, email, provider, provider_subject, is_active, is_verified, created_at, updated_at)
VALUES (
    'usr-shivraj-001',
    'shivraj.dhote@finex.internal',
    'development',
    'dev-sub-shivraj-001',
    TRUE,
    TRUE,
    NOW(),
    NOW()
)
ON CONFLICT (id) DO NOTHING;

-- User Profile (Initialized cleanly without fabricated risk assessment or consent)
INSERT INTO user_profiles (id, user_id, full_name, display_name, country, experience_level, onboarding_completed, risk_band, composite_score, risk_assessment, created_at, updated_at)
VALUES (
    'prof-shivraj-001',
    'usr-shivraj-001',
    'Shivraj Dhote',
    'Shivraj',
    'IND',
    'BEGINNER',
    FALSE,
    'MODERATE',
    50.00,
    NULL,
    NOW(),
    NOW()
)
ON CONFLICT (id) DO NOTHING;

-- Virtual Paper Trading Account (₹10,00,000 cash balance)
INSERT INTO paper_accounts (id, user_id, account_number, currency, status, cash_balance, current_cash, initial_balance, total_realized_pnl, total_trades_count, reset_count, created_at, updated_at)
VALUES (
    'acc-shivraj-001',
    'usr-shivraj-001',
    'FINEX-VIRT-7001',
    'INR',
    'ACTIVE',
    1000000.00,
    1000000.00,
    1000000.00,
    0.00,
    0,
    0,
    NOW(),
    NOW()
)
ON CONFLICT (id) DO NOTHING;

-- Initial Paper Cash Ledger Credit
INSERT INTO paper_cash_ledger (id, account_id, entry_type, amount, balance_after, reference_id, description, created_at)
VALUES (
    'led-shivraj-init-001',
    'acc-shivraj-001',
    'INITIAL_CREDIT',
    1000000.00,
    1000000.00,
    'INIT-CREDIT-7001',
    'Initial virtual paper trading cash credit',
    NOW()
)
ON CONFLICT (id) DO NOTHING;

-- Default Financial Goals
INSERT INTO financial_goals (id, user_id, title, category, target_amount, current_amount, currency, target_date, assumed_annual_return_pct, status, created_at, updated_at)
VALUES
    ('goal-emergency-001', 'usr-shivraj-001', 'Emergency Reserve Fund', 'EMERGENCY', 300000.00, 150000.00, 'INR', '2027-12-31', 6.50, 'ACTIVE', NOW(), NOW()),
    ('goal-wealth-002', 'usr-shivraj-001', 'Index Wealth Portfolio', 'INVESTMENT', 1500000.00, 420000.00, 'INR', '2030-03-31', 11.50, 'ACTIVE', NOW(), NOW())
ON CONFLICT (id) DO NOTHING;

-- Core Securities & Indexes
INSERT INTO securities (id, symbol, name, exchange, currency, asset_class, sector, is_active, created_at, updated_at) VALUES
    ('sec-reliance', 'RELIANCE', 'Reliance Industries Ltd', 'NSE', 'INR', 'EQUITY', 'Energy / Conglomerate', TRUE, NOW(), NOW()),
    ('sec-tcs', 'TCS', 'Tata Consultancy Services Ltd', 'NSE', 'INR', 'EQUITY', 'Information Technology', TRUE, NOW(), NOW()),
    ('sec-infy', 'INFY', 'Infosys Ltd', 'NSE', 'INR', 'EQUITY', 'Information Technology', TRUE, NOW(), NOW()),
    ('sec-hdfcbank', 'HDFCBANK', 'HDFC Bank Ltd', 'NSE', 'INR', 'EQUITY', 'Financial Services', TRUE, NOW(), NOW()),
    ('sec-icicibank', 'ICICIBANK', 'ICICI Bank Ltd', 'NSE', 'INR', 'EQUITY', 'Financial Services', TRUE, NOW(), NOW()),
    ('sec-nifty50', 'NIFTY 50', 'Nifty 50 Index', 'NSE', 'INR', 'INDEX', 'Broad Market', TRUE, NOW(), NOW())
ON CONFLICT (symbol) DO NOTHING;

-- Core Regulatory Documents for Grounded AI RAG
INSERT INTO document_registry (id, title, source_url, publisher, doc_type, publishing_date, content_hash, status, created_at) VALUES
    ('rag-doc-sebi-ria', 'SEBI Investment Advisers Regulations 2013 and Amendments', 'https://www.sebi.gov.in/legal/regulations/jan-2021/securities-and-exchange-board-of-india-investment-advisers-regulations-2013-last-amended-on-january-11-2021-_48711.html', 'SEBI', 'REGULATION', '2021-01-11', 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'ACTIVE', NOW()),
    ('rag-doc-rbi-kyc', 'Reserve Bank of India Master Direction - Know Your Customer (KYC) Direction 2016', 'https://www.rbi.org.in/Scripts/BS_ViewMasDirections.aspx?id=11566', 'RBI', 'MASTER_DIRECTION', '2023-05-04', 'a591a6d40bf420404a011733cfb7b190d62c65bf0bcda32b57b277d9ad9f146e', 'ACTIVE', NOW()),
    ('rag-doc-nse-margin', 'NSE Consolidated Circular on Margin Trading Facility (MTF) & Risk Containment', 'https://www.nseindia.com/regulations/member-circulars', 'NSE', 'CIRCULAR', '2024-01-15', '5be3b6a988185c8846c8273612807f6e026b484501a91e3e7855b4fd8c3f4e3c', 'ACTIVE', NOW())
ON CONFLICT (id) DO NOTHING;

-- ============================================================================
-- 10. ALEMBIC MIGRATION BASELINE STAMP
-- ============================================================================
CREATE TABLE IF NOT EXISTS alembic_version (
    version_num VARCHAR(32) NOT NULL,
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);
INSERT INTO alembic_version (version_num) VALUES ('5c7e81d9f012')
ON CONFLICT DO NOTHING;
