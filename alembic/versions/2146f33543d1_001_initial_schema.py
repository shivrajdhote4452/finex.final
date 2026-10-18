"""001_initial_schema

Revision ID: 2146f33543d1
Revises:
Create Date: 2026-10-16 22:02:37.969925
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2146f33543d1"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# UUID type with SQLite fallback
uuid_type = sa.String(36).with_variant(postgresql.UUID(as_uuid=True), "postgresql")
json_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    # 1. users
    op.create_table(
        "users",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("provider", sa.String(50), nullable=False, server_default="google"),
        sa.Column("provider_subject", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("provider", "provider_subject", name="uq_users_provider_subject"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    # 2. user_profiles (initial baseline without risk fields added in 003)
    op.create_table(
        "user_profiles",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.String(64), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("display_name", sa.String(100), nullable=True),
        sa.Column("country", sa.String(3), nullable=False, server_default="IND"),
        sa.Column("experience_level", sa.String(50), nullable=False, server_default="BEGINNER"),
        sa.Column("onboarding_completed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 3. user_consents
    op.create_table(
        "user_consents",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.String(64), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("consent_version", sa.String(50), nullable=False),
        sa.Column("terms_accepted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("privacy_accepted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("educational_disclaimer_accepted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.UniqueConstraint("user_id", "consent_version", name="uq_user_consent_version"),
    )
    op.create_index("ix_user_consents_user_id", "user_consents", ["user_id"])

    # 4. portfolios
    op.create_table(
        "portfolios",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.String(64), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False, server_default="My Primary Portfolio"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("currency", sa.String(3), nullable=False, server_default="INR"),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_portfolios_user_id", "portfolios", ["user_id"])

    # 5. portfolio_holdings
    op.create_table(
        "portfolio_holdings",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("portfolio_id", sa.String(64), sa.ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False),
        sa.Column("symbol", sa.String(50), nullable=False),
        sa.Column("asset_class", sa.String(50), nullable=False, server_default="EQUITY"),
        sa.Column("quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("cost_basis_per_share", sa.Numeric(18, 4), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="INR"),
        sa.Column("purchase_date", sa.Date(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("quantity > 0", name="chk_holdings_quantity_positive"),
        sa.CheckConstraint("cost_basis_per_share >= 0", name="chk_holdings_cost_basis_non_negative"),
        sa.UniqueConstraint("portfolio_id", "symbol", "purchase_date", name="uq_portfolio_symbol_purchase"),
    )
    op.create_index("ix_portfolio_holdings_portfolio_id", "portfolio_holdings", ["portfolio_id"])
    op.create_index("ix_portfolio_holdings_symbol", "portfolio_holdings", ["symbol"])

    # 6. application_events
    op.create_table(
        "application_events",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.String(64), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("correlation_id", sa.String(100), nullable=False),
        sa.Column("payload", json_type, nullable=False),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_application_events_user_id", "application_events", ["user_id"])
    op.create_index("ix_application_events_correlation_id", "application_events", ["correlation_id"])

    # 7. securities
    op.create_table(
        "securities",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("symbol", sa.String(20), nullable=False, unique=True),
        sa.Column("canonical_id", sa.String(70), nullable=True, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("isin", sa.String(12), nullable=True, unique=True),
        sa.Column("exchange", sa.String(10), nullable=False, server_default="NSE"),
        sa.Column("currency", sa.String(3), nullable=False, server_default="INR"),
        sa.Column("asset_class", sa.String(50), nullable=False, server_default="EQUITY"),
        sa.Column("sector", sa.String(100), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_securities_symbol", "securities", ["symbol"])

    # 8. market_price_history
    op.create_table(
        "market_price_history",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("security_id", uuid_type, sa.ForeignKey("securities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("price_date", sa.Date(), nullable=True),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("open_price", sa.Numeric(14, 4), nullable=False),
        sa.Column("high_price", sa.Numeric(14, 4), nullable=False),
        sa.Column("low_price", sa.Numeric(14, 4), nullable=False),
        sa.Column("close_price", sa.Numeric(14, 4), nullable=False),
        sa.Column("adjusted_close", sa.Numeric(14, 4), nullable=True),
        sa.Column("adj_close_price", sa.Numeric(14, 4), nullable=False),
        sa.Column("volume", sa.BigInteger(), nullable=False),
        sa.Column("data_source", sa.String(50), nullable=True, server_default="nse"),
        sa.Column("source", sa.String(50), nullable=False, server_default="NSE_EOD"),
        sa.Column("currency", sa.String(3), nullable=False, server_default="INR"),
        sa.Column("is_interpolated", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("security_id", "trade_date", "source", name="uq_price_history_natural_key"),
    )
    op.create_index("ix_market_price_history_security_id", "market_price_history", ["security_id"])
    op.create_index("ix_market_price_history_trade_date", "market_price_history", ["trade_date"])

    # 9. market_quotes
    op.create_table(
        "market_quotes",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("security_id", uuid_type, sa.ForeignKey("securities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("symbol", sa.String(20), nullable=True),
        sa.Column("price", sa.Numeric(14, 4), nullable=False),
        sa.Column("last_price", sa.Numeric(14, 4), nullable=True),
        sa.Column("change", sa.Numeric(14, 4), nullable=False, server_default="0.0000"),
        sa.Column("change_amount", sa.Numeric(14, 4), nullable=True),
        sa.Column("change_pct", sa.Numeric(8, 4), nullable=False, server_default="0.0000"),
        sa.Column("change_percentage", sa.Numeric(8, 4), nullable=True),
        sa.Column("previous_close", sa.Numeric(14, 4), nullable=False),
        sa.Column("open_price", sa.Numeric(14, 4), nullable=True),
        sa.Column("high_price", sa.Numeric(14, 4), nullable=True),
        sa.Column("low_price", sa.Numeric(14, 4), nullable=True),
        sa.Column("volume", sa.BigInteger(), nullable=True),
        sa.Column("currency", sa.String(3), nullable=False, server_default="INR"),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("quote_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("freshness_status", sa.String(20), nullable=False, server_default="LIVE"),
        sa.Column("served_from_cache", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_delayed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(50), nullable=False, server_default="nse_realtime"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_market_quotes_security_id", "market_quotes", ["security_id"])
    op.create_index("ix_market_quotes_observed_at", "market_quotes", ["observed_at"])

    # 10. watchlists
    op.create_table(
        "watchlists",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("user_id", sa.String(64), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_watchlists_user_id", "watchlists", ["user_id"])

    # 11. watchlist_items
    op.create_table(
        "watchlist_items",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("watchlist_id", uuid_type, sa.ForeignKey("watchlists.id", ondelete="CASCADE"), nullable=False),
        sa.Column("security_id", uuid_type, sa.ForeignKey("securities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("watchlist_id", "security_id", name="uq_watchlist_security"),
    )
    op.create_index("ix_watchlist_items_watchlist_id", "watchlist_items", ["watchlist_id"])
    op.create_index("ix_watchlist_items_security_id", "watchlist_items", ["security_id"])

    # 12. alert_rules
    op.create_table(
        "alert_rules",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("user_id", sa.String(64), nullable=False),
        sa.Column("rule_type", sa.String(32), nullable=False),
        sa.Column("symbol", sa.String(16), nullable=True),
        sa.Column("comparison_operator", sa.String(8), nullable=False),
        sa.Column("threshold_value", sa.Numeric(14, 4), nullable=False),
        sa.Column("threshold_unit", sa.String(16), nullable=False),
        sa.Column("cooldown_minutes", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_triggered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_alert_rules_user_id", "alert_rules", ["user_id"])

    # 13. alert_events
    op.create_table(
        "alert_events",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("rule_id", uuid_type, sa.ForeignKey("alert_rules.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(64), nullable=False),
        sa.Column("event_type", sa.String(32), nullable=False, server_default="PRICE_ALERT"),
        sa.Column("symbol", sa.String(20), nullable=True),
        sa.Column("triggered_value", sa.Numeric(14, 4), nullable=False, server_default="0.0000"),
        sa.Column("threshold_value", sa.Numeric(14, 4), nullable=False, server_default="0.0000"),
        sa.Column("title", sa.String(255), nullable=False, server_default="Alert Triggered"),
        sa.Column("message", sa.Text(), nullable=False, server_default=""),
        sa.Column("dedupe_key", sa.String(128), nullable=True, unique=True),
        sa.Column("event_payload", json_type, nullable=True),
        sa.Column("triggered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_alert_events_user_id", "alert_events", ["user_id"])
    op.create_index("ix_alert_events_rule_id", "alert_events", ["rule_id"])
    op.create_index("ix_alert_events_dedupe_key", "alert_events", ["dedupe_key"])

    # 14. notifications
    op.create_table(
        "notifications",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("user_id", sa.String(64), nullable=False),
        sa.Column("alert_event_id", uuid_type, sa.ForeignKey("alert_events.id", ondelete="SET NULL"), nullable=True),
        sa.Column("category", sa.String(32), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index("ix_notifications_is_read", "notifications", ["is_read"])
    op.create_index("ix_notifications_created_at", "notifications", ["created_at"])

    # 15. notification_delivery_attempts
    op.create_table(
        "notification_delivery_attempts",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("notification_id", uuid_type, sa.ForeignKey("notifications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("channel", sa.String(16), nullable=False),
        sa.Column("attempt_status", sa.String(16), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("response_payload", json_type, nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("attempted_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_notification_delivery_attempts_notification_id", "notification_delivery_attempts", ["notification_id"])

    # 16. financial_goals
    op.create_table(
        "financial_goals",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("user_id", sa.String(64), nullable=False),
        sa.Column("title", sa.String(128), nullable=False),
        sa.Column("category", sa.String(32), nullable=False),
        sa.Column("target_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("current_amount", sa.Numeric(14, 2), nullable=False, server_default="0.00"),
        sa.Column("currency", sa.String(8), nullable=False, server_default="INR"),
        sa.Column("target_date", sa.Date(), nullable=False),
        sa.Column("assumed_annual_return_pct", sa.Numeric(5, 2), nullable=False, server_default="8.00"),
        sa.Column("status", sa.String(16), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_financial_goals_user_id", "financial_goals", ["user_id"])
    op.create_index("ix_financial_goals_target_date", "financial_goals", ["target_date"])

    # 17. goal_contributions
    op.create_table(
        "goal_contributions",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("goal_id", uuid_type, sa.ForeignKey("financial_goals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(64), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("contribution_date", sa.Date(), nullable=False),
        sa.Column("notes", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_goal_contributions_goal_id", "goal_contributions", ["goal_id"])
    op.create_index("ix_goal_contributions_user_id", "goal_contributions", ["user_id"])
    op.create_index("ix_goal_contributions_contribution_date", "goal_contributions", ["contribution_date"])

    # 18. goal_projections
    op.create_table(
        "goal_projections",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("goal_id", uuid_type, sa.ForeignKey("financial_goals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(64), nullable=False, server_default="usr-shivraj-001"),
        sa.Column("projection_date", sa.Date(), nullable=False),
        sa.Column("projected_amount", sa.Numeric(14, 2), nullable=False, server_default="0.00"),
        sa.Column("projected_future_value", sa.Numeric(14, 2), nullable=True),
        sa.Column("shortfall_surplus", sa.Numeric(14, 2), nullable=False, server_default="0.00"),
        sa.Column("confidence_interval_low", sa.Numeric(14, 2), nullable=False, server_default="0.00"),
        sa.Column("confidence_interval_high", sa.Numeric(14, 2), nullable=False, server_default="0.00"),
        sa.Column("required_monthly_savings", sa.Numeric(14, 2), nullable=True),
        sa.Column("months_remaining", sa.Integer(), nullable=True),
        sa.Column("formula_version", sa.String(16), nullable=False, server_default="v1.0"),
        sa.Column("assumptions_version", sa.String(32), nullable=True),
        sa.Column("assumptions_payload", json_type, nullable=False, server_default="{}"),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_goal_projections_goal_id", "goal_projections", ["goal_id"])
    op.create_index("ix_goal_projections_user_id", "goal_projections", ["user_id"])

    # 19. transaction_uploads (initial baseline without unique constraint added in 002)
    op.create_table(
        "transaction_uploads",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("user_id", sa.String(64), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("file_hash_sha256", sa.String(64), nullable=False),
        sa.Column("total_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("accepted_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("quarantined_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(16), nullable=False, server_default="COMMITTED"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_transaction_uploads_user_id", "transaction_uploads", ["user_id"])
    op.create_index("ix_transaction_uploads_file_hash_sha256", "transaction_uploads", ["file_hash_sha256"])

    # 20. transaction_categories
    op.create_table(
        "transaction_categories",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("is_essential", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 21. transactions (initial baseline without unique constraint added in 002)
    op.create_table(
        "transactions",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("upload_id", uuid_type, sa.ForeignKey("transaction_uploads.id", ondelete="SET NULL"), nullable=True),
        sa.Column("user_id", sa.String(64), nullable=False),
        sa.Column("transaction_date", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("transaction_type", sa.String(8), nullable=False),
        sa.Column("masked_description", sa.String(255), nullable=False),
        sa.Column("category_id", sa.String(32), sa.ForeignKey("transaction_categories.id"), nullable=False),
        sa.Column("categorization_method", sa.String(16), nullable=False),
        sa.Column("confidence_score", sa.Numeric(3, 2), nullable=False),
        sa.Column("is_reviewed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("dedupe_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_transactions_user_id", "transactions", ["user_id"])
    op.create_index("ix_transactions_transaction_date", "transactions", ["transaction_date"])
    op.create_index("ix_transactions_category_id", "transactions", ["category_id"])
    op.create_index("ix_transactions_dedupe_hash", "transactions", ["dedupe_hash"])

    # 22. monthly_spending_summaries
    op.create_table(
        "monthly_spending_summaries",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("user_id", sa.String(64), nullable=False),
        sa.Column("year_month", sa.String(7), nullable=False),
        sa.Column("total_debit", sa.Numeric(14, 2), nullable=False, server_default="0.00"),
        sa.Column("total_credit", sa.Numeric(14, 2), nullable=False, server_default="0.00"),
        sa.Column("net_savings", sa.Numeric(14, 2), nullable=False, server_default="0.00"),
        sa.Column("savings_rate_pct", sa.Numeric(5, 2), nullable=False, server_default="0.00"),
        sa.Column("transaction_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("category_breakdown", json_type, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "year_month", name="uq_user_monthly_summary"),
    )
    op.create_index("ix_monthly_spending_summaries_user_id", "monthly_spending_summaries", ["user_id"])

    # 23. paper_accounts
    op.create_table(
        "paper_accounts",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.String(64), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("account_number", sa.String(32), nullable=False, server_default="ACC-DEFAULT", unique=True),
        sa.Column("currency", sa.String(3), nullable=False, server_default="INR"),
        sa.Column("status", sa.String(20), nullable=False, server_default="ACTIVE"),
        sa.Column("cash_balance", sa.Numeric(14, 2), nullable=False, server_default="100000.00"),
        sa.Column("current_cash", sa.Numeric(14, 2), nullable=False, server_default="100000.00"),
        sa.Column("initial_balance", sa.Numeric(14, 2), nullable=False, server_default="100000.00"),
        sa.Column("total_realized_pnl", sa.Numeric(14, 2), nullable=False, server_default="0.00"),
        sa.Column("total_trades_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reset_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    # 24. paper_orders (initial baseline without execution_receipt added in 002)
    op.create_table(
        "paper_orders",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("account_id", sa.String(64), sa.ForeignKey("paper_accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(64), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("side", sa.String(10), nullable=False),
        sa.Column("order_type", sa.String(20), nullable=False),
        sa.Column("quantity", sa.Numeric(14, 4), nullable=False),
        sa.Column("limit_price", sa.Numeric(14, 2), nullable=True),
        sa.Column("fill_price", sa.Numeric(14, 2), nullable=True),
        sa.Column("fee", sa.Numeric(14, 2), nullable=False, server_default="0.00"),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("rejection_reason", sa.String(255), nullable=True),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("account_id", "idempotency_key", name="uq_paper_order_idempotency"),
    )

    # 25. paper_trades
    op.create_table(
        "paper_trades",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("order_id", sa.String(64), sa.ForeignKey("paper_orders.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("account_id", sa.String(64), sa.ForeignKey("paper_accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("side", sa.String(10), nullable=False),
        sa.Column("quantity", sa.Numeric(14, 4), nullable=False),
        sa.Column("price", sa.Numeric(14, 2), nullable=False),
        sa.Column("gross_value", sa.Numeric(14, 2), nullable=False),
        sa.Column("fee", sa.Numeric(14, 2), nullable=False, server_default="0.00"),
        sa.Column("net_value", sa.Numeric(14, 2), nullable=False),
        sa.Column("execution_time", sa.DateTime(timezone=True), nullable=True),
    )

    # 26. paper_positions
    op.create_table(
        "paper_positions",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("account_id", sa.String(64), sa.ForeignKey("paper_accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("quantity", sa.Numeric(14, 4), nullable=False),
        sa.Column("average_buy_price", sa.Numeric(14, 2), nullable=False),
        sa.Column("total_cost_basis", sa.Numeric(14, 2), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("account_id", "symbol", name="uq_paper_position_symbol"),
    )

    # 27. paper_cash_ledger
    op.create_table(
        "paper_cash_ledger",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("account_id", sa.String(64), sa.ForeignKey("paper_accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entry_type", sa.String(30), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("balance_after", sa.Numeric(14, 2), nullable=False),
        sa.Column("reference_id", sa.String(64), nullable=True),
        sa.Column("description", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )

    # 28. ai_conversations
    op.create_table(
        "ai_conversations",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.String(64), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=True, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_ai_conversations_user_id", "ai_conversations", ["user_id"])

    # 29. ai_messages
    op.create_table(
        "ai_messages",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("conversation_id", sa.String(64), sa.ForeignKey("ai_conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(64), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("intent_detected", sa.String(50), nullable=True),
        sa.Column("correlation_id", sa.String(64), nullable=False),
        sa.Column("latency_ms", sa.Float(), nullable=True),
        sa.Column("model_version", sa.String(50), nullable=True),
        sa.Column("is_fallback", sa.Boolean(), nullable=True, server_default=sa.false()),
        sa.Column("citation_chunk_ids", json_type, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )

    # 30. ai_feedback
    op.create_table(
        "ai_feedback",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("message_id", sa.String(64), sa.ForeignKey("ai_messages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(64), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("feedback_type", sa.String(50), nullable=True),
        sa.Column("comments", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("user_id", "message_id", name="uq_user_message_feedback"),
    )

    # 31. document_registry
    op.create_table(
        "document_registry",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("document_id", sa.String(64), nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("doc_type", sa.String(50), nullable=False, server_default="REGULATION"),
        sa.Column("publisher", sa.String(128), nullable=False),
        sa.Column("publishing_date", sa.Date(), nullable=False, server_default=sa.func.current_date()),
        sa.Column("published_date", sa.Date(), nullable=True),
        sa.Column("reporting_period", sa.String(50), nullable=True),
        sa.Column("security_symbol", sa.String(20), nullable=True),
        sa.Column("isin", sa.String(20), nullable=True),
        sa.Column("source_url", sa.String(512), nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=False, server_default="sha256-pending"),
        sa.Column("content_hash_sha256", sa.String(64), nullable=True),
        sa.Column("retrieval_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("chunk_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="ACTIVE"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_document_registry_title", "document_registry", ["title"])

    # 32. document_chunks
    op.create_table(
        "document_chunks",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("document_id", sa.String(64), sa.ForeignKey("document_registry.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False, server_default=""),
        sa.Column("chunk_text", sa.Text(), nullable=True),
        sa.Column("section_title", sa.String(255), nullable=True),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("word_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column("embedding_vector", json_type, nullable=True),
        sa.Column("embedding_vector_id", sa.String(128), nullable=True),
        sa.Column("metadata", json_type, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("document_id", "chunk_index", name="uq_doc_chunk"),
    )
    op.create_index("ix_document_chunks_document_id", "document_chunks", ["document_id"])

    # 33. retrieval_events
    op.create_table(
        "retrieval_events",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("correlation_id", sa.String(64), nullable=False),
        sa.Column("conversation_id", sa.String(64), nullable=True),
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column("filter_metadata", json_type, nullable=True),
        sa.Column("top_k", sa.Integer(), nullable=False),
        sa.Column("retrieved_chunk_ids", json_type, nullable=True),
        sa.Column("latency_ms", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    for tbl in [
        "retrieval_events",
        "document_chunks",
        "document_registry",
        "ai_feedback",
        "ai_messages",
        "ai_conversations",
        "paper_cash_ledger",
        "paper_positions",
        "paper_trades",
        "paper_orders",
        "paper_accounts",
        "monthly_spending_summaries",
        "transactions",
        "transaction_categories",
        "transaction_uploads",
        "goal_projections",
        "goal_contributions",
        "financial_goals",
        "notification_delivery_attempts",
        "notifications",
        "alert_events",
        "alert_rules",
        "watchlist_items",
        "watchlists",
        "market_quotes",
        "market_price_history",
        "securities",
        "application_events",
        "portfolio_holdings",
        "portfolios",
        "user_consents",
        "user_profiles",
        "users",
    ]:
        op.drop_table(tbl)
