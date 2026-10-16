-- ==============================================================================
-- FINEX FINANCIAL EXCELLENCE PLATFORM
-- Module: Financial Goals, Projections, and Contributions
-- Author: Shivraj Dhote
-- Sprint: 7 (S7-DAT-01)
-- Date: 16 October 2026
-- ==============================================================================

-- 1. Financial Goals Master
CREATE TABLE IF NOT EXISTS financial_goals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(64) NOT NULL,
    title VARCHAR(128) NOT NULL,
    category VARCHAR(32) NOT NULL CHECK (category IN ('RETIREMENT', 'EMERGENCY_FUND', 'HOME_PURCHASE', 'EDUCATION', 'TRAVEL', 'WEALTH_CREATION', 'CUSTOM')),
    target_amount NUMERIC(14, 2) NOT NULL CHECK (target_amount > 0),
    current_amount NUMERIC(14, 2) NOT NULL DEFAULT 0.00 CHECK (current_amount >= 0),
    currency VARCHAR(8) NOT NULL DEFAULT 'INR',
    target_date DATE NOT NULL,
    assumed_annual_return_pct NUMERIC(5, 2) NOT NULL DEFAULT 8.00 CHECK (assumed_annual_return_pct >= 0 AND assumed_annual_return_pct <= 30.00),
    status VARCHAR(16) NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'COMPLETED', 'ARCHIVED', 'PAUSED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_financial_goals_user ON financial_goals(user_id, status);
CREATE INDEX IF NOT EXISTS idx_financial_goals_target_date ON financial_goals(target_date);

-- 2. Goal Contributions (Append-only audit trail)
CREATE TABLE IF NOT EXISTS goal_contributions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    goal_id UUID NOT NULL REFERENCES financial_goals(id) ON DELETE CASCADE,
    user_id VARCHAR(64) NOT NULL,
    amount NUMERIC(14, 2) NOT NULL CHECK (amount > 0),
    contribution_date DATE NOT NULL,
    notes VARCHAR(255) NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_goal_contributions_goal ON goal_contributions(goal_id, contribution_date DESC);
CREATE INDEX IF NOT EXISTS idx_goal_contributions_user ON goal_contributions(user_id);

-- 3. Goal Projections History (Versioned mathematical outputs)
CREATE TABLE IF NOT EXISTS goal_projections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    goal_id UUID NOT NULL REFERENCES financial_goals(id) ON DELETE CASCADE,
    user_id VARCHAR(64) NOT NULL,
    formula_version VARCHAR(32) NOT NULL DEFAULT 'fv_compound_monthly_v1.0',
    months_remaining INT NOT NULL,
    projected_future_value NUMERIC(14, 2) NOT NULL,
    required_monthly_savings NUMERIC(14, 2) NOT NULL,
    shortfall_surplus NUMERIC(14, 2) NOT NULL,
    assumptions_payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_goal_projections_goal ON goal_projections(goal_id, created_at DESC);

-- 4. Goal Progress Snapshots (Periodic historical checkpoint)
CREATE TABLE IF NOT EXISTS goal_progress_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    goal_id UUID NOT NULL REFERENCES financial_goals(id) ON DELETE CASCADE,
    snapshot_date DATE NOT NULL,
    accumulated_amount NUMERIC(14, 2) NOT NULL,
    progress_pct NUMERIC(5, 2) NOT NULL,
    is_on_track BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_goal_progress_snapshots ON goal_progress_snapshots(goal_id, snapshot_date DESC);
