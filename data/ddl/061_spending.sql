-- ==============================================================================
-- FINEX FINANCIAL EXCELLENCE PLATFORM
-- Module: Spending Analysis, CSV Ingestion, and Categorization
-- Author: Shivraj Dhote
-- Sprint: 7 (S7-DAT-02)
-- Date: 16 October 2026
-- ==============================================================================

-- 1. Transaction Uploads (Batch metadata and hash deduplication)
CREATE TABLE IF NOT EXISTS transaction_uploads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(64) NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_hash_sha256 VARCHAR(64) NOT NULL,
    total_rows INT NOT NULL DEFAULT 0,
    accepted_rows INT NOT NULL DEFAULT 0,
    quarantined_rows INT NOT NULL DEFAULT 0,
    status VARCHAR(16) NOT NULL DEFAULT 'COMMITTED' CHECK (status IN ('PREVIEW', 'COMMITTED', 'REJECTED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_transaction_uploads_user ON transaction_uploads(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_transaction_uploads_hash ON transaction_uploads(user_id, file_hash_sha256);

-- 2. Transaction Categories Master
CREATE TABLE IF NOT EXISTS transaction_categories (
    id VARCHAR(32) PRIMARY KEY,
    name VARCHAR(64) NOT NULL,
    description VARCHAR(255) NULL,
    is_essential BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Seed standard baseline taxonomy
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

-- 3. Transactions Master (Masked descriptions for privacy protection)
CREATE TABLE IF NOT EXISTS transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    upload_id UUID NULL REFERENCES transaction_uploads(id) ON DELETE SET NULL,
    user_id VARCHAR(64) NOT NULL,
    transaction_date DATE NOT NULL,
    amount NUMERIC(14, 2) NOT NULL CHECK (amount > 0),
    transaction_type VARCHAR(8) NOT NULL CHECK (transaction_type IN ('DEBIT', 'CREDIT')),
    masked_description VARCHAR(255) NOT NULL,
    category_id VARCHAR(32) NOT NULL REFERENCES transaction_categories(id),
    categorization_method VARCHAR(16) NOT NULL DEFAULT 'RULE' CHECK (categorization_method IN ('RULE', 'AI_FALLBACK', 'USER_CORRECTED')),
    confidence_score NUMERIC(3, 2) NOT NULL DEFAULT 1.00,
    is_reviewed BOOLEAN NOT NULL DEFAULT FALSE,
    dedupe_hash VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_transactions_user_date ON transactions(user_id, transaction_date DESC);
CREATE INDEX IF NOT EXISTS idx_transactions_category ON transactions(user_id, category_id);
CREATE INDEX IF NOT EXISTS idx_transactions_dedupe ON transactions(user_id, dedupe_hash);

-- 4. Monthly Spending Summaries (Analytical aggregation)
CREATE TABLE IF NOT EXISTS monthly_spending_summaries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(64) NOT NULL,
    year_month VARCHAR(7) NOT NULL, -- Format: YYYY-MM
    total_debit NUMERIC(14, 2) NOT NULL DEFAULT 0.00,
    total_credit NUMERIC(14, 2) NOT NULL DEFAULT 0.00,
    net_savings NUMERIC(14, 2) NOT NULL DEFAULT 0.00,
    savings_rate_pct NUMERIC(5, 2) NOT NULL DEFAULT 0.00,
    category_breakdown JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_user_month UNIQUE(user_id, year_month)
);

CREATE INDEX IF NOT EXISTS idx_monthly_spending_user ON monthly_spending_summaries(user_id, year_month DESC);
