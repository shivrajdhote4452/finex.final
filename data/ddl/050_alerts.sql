-- ==============================================================================
-- FINEX FINANCIAL EXCELLENCE PLATFORM
-- Module: Smart Alerts, Notifications, and Notification Delivery
-- Author: Shivraj Dhote
-- Sprint: 6 (S6-DAT-01)
-- Date: 16 October 2026
-- ==============================================================================

-- 1. Alert Rules: User-configured deterministic triggers
CREATE TABLE IF NOT EXISTS alert_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(64) NOT NULL,
    rule_type VARCHAR(32) NOT NULL CHECK (rule_type IN ('PRICE_ABOVE', 'PRICE_BELOW', 'PERCENT_CHANGE_UP', 'PERCENT_CHANGE_DOWN', 'CONCENTRATION_EXCEEDED', 'RISK_CHANGE', 'GOAL_OFF_TRACK')),
    symbol VARCHAR(20) NULL,
    comparison_operator VARCHAR(8) NOT NULL CHECK (comparison_operator IN ('>=', '<=', '>', '<', '=')),
    threshold_value NUMERIC(14, 4) NOT NULL,
    threshold_unit VARCHAR(16) NOT NULL CHECK (threshold_unit IN ('INR', 'PERCENT', 'RATIO')),
    cooldown_minutes INT NOT NULL DEFAULT 60 CHECK (cooldown_minutes >= 5),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_triggered_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_alert_rules_user ON alert_rules(user_id, is_active);
CREATE INDEX IF NOT EXISTS idx_alert_rules_type ON alert_rules(rule_type, is_active);
CREATE INDEX IF NOT EXISTS idx_alert_rules_symbol ON alert_rules(symbol) WHERE symbol IS NOT NULL;

-- 2. Alert Events: Generated instances when an alert rule condition is met
CREATE TABLE IF NOT EXISTS alert_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_id UUID NOT NULL REFERENCES alert_rules(id) ON DELETE CASCADE,
    user_id VARCHAR(64) NOT NULL,
    event_type VARCHAR(32) NOT NULL,
    symbol VARCHAR(20) NULL,
    triggered_value NUMERIC(14, 4) NOT NULL,
    threshold_value NUMERIC(14, 4) NOT NULL,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    dedupe_key VARCHAR(128) NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_alert_events_user ON alert_events(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_alert_events_rule ON alert_events(rule_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_alert_events_dedupe ON alert_events(dedupe_key);

-- 3. Notifications: Operational user in-app notification center
CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(64) NOT NULL,
    alert_event_id UUID NULL REFERENCES alert_events(id) ON DELETE SET NULL,
    category VARCHAR(32) NOT NULL CHECK (category IN ('PRICE_ALERT', 'PORTFOLIO_RISK', 'SYSTEM_NOTICE', 'GOAL_ALERT')),
    title VARCHAR(255) NOT NULL,
    body TEXT NOT NULL,
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    read_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_notifications_user_unread ON notifications(user_id, is_read, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_notifications_user_all ON notifications(user_id, created_at DESC);

-- 4. Notification Delivery Attempts: Append-only audit trail for multi-channel delivery
CREATE TABLE IF NOT EXISTS notification_delivery_attempts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    notification_id UUID NOT NULL REFERENCES notifications(id) ON DELETE CASCADE,
    channel VARCHAR(16) NOT NULL CHECK (channel IN ('IN_APP', 'PUSH_FCM', 'EMAIL', 'WEBHOOK')),
    attempt_status VARCHAR(16) NOT NULL CHECK (attempt_status IN ('SUCCESS', 'FAILED', 'PENDING')),
    attempt_number INT NOT NULL DEFAULT 1,
    response_payload JSONB NULL,
    error_message TEXT NULL,
    attempted_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_delivery_attempts_notif ON notification_delivery_attempts(notification_id, attempted_at DESC);
CREATE INDEX IF NOT EXISTS idx_delivery_attempts_status ON notification_delivery_attempts(channel, attempt_status);
