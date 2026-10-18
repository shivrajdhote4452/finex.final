"""004_schema_compatibility

Revision ID: 5c7e81d9f012
Revises: 4b6f23a8c7e5
Create Date: 2026-10-18 13:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import context, op

revision: str = "5c7e81d9f012"
down_revision: Union[str, Sequence[str], None] = "4b6f23a8c7e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

json_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    if context.is_offline_mode():
        # Offline DDL generation
        with op.batch_alter_table("paper_accounts") as batch_op:
            batch_op.add_column(sa.Column("status", sa.String(20), nullable=False, server_default="ACTIVE"))
            batch_op.add_column(sa.Column("account_number", sa.String(32), nullable=False, server_default="ACC-DEFAULT"))
        with op.batch_alter_table("goal_contributions") as batch_op:
            batch_op.add_column(sa.Column("user_id", sa.String(64), nullable=False, server_default="usr-shivraj-001"))
            batch_op.create_index("ix_goal_contributions_user_id", ["user_id"])
        with op.batch_alter_table("ai_conversations") as batch_op:
            batch_op.add_column(sa.Column("is_deleted", sa.Boolean(), nullable=True, server_default=sa.false()))
        with op.batch_alter_table("securities") as batch_op:
            batch_op.add_column(sa.Column("canonical_id", sa.String(70), nullable=True))
            batch_op.create_unique_constraint("uq_securities_canonical_id", ["canonical_id"])
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
        op.create_table(
            "transaction_previews",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("user_id", sa.String(64), nullable=False),
            sa.Column("file_name", sa.String(255), nullable=False),
            sa.Column("file_hash_sha256", sa.String(64), nullable=False),
            sa.Column("total_rows", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("valid_rows", json_type, nullable=False),
            sa.Column("duplicate_rows", json_type, nullable=False),
            sa.Column("invalid_rows", json_type, nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
            sa.Column("committed_upload_id", sa.String(64), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_transaction_previews_user_id", "transaction_previews", ["user_id"])
        op.create_index("ix_transaction_previews_file_hash", "transaction_previews", ["file_hash_sha256"])
        return

    from sqlalchemy import inspect
    bind = op.get_bind()
    insp = inspect(bind)
    tables = set(insp.get_table_names())

    # 1. Forward migration for paper_accounts.status and account_number
    if "paper_accounts" in tables:
        acct_cols = [c["name"] for c in insp.get_columns("paper_accounts")]
        with op.batch_alter_table("paper_accounts") as batch_op:
            if "status" not in acct_cols:
                batch_op.add_column(sa.Column("status", sa.String(20), nullable=False, server_default="ACTIVE"))
            if "account_number" not in acct_cols:
                batch_op.add_column(sa.Column("account_number", sa.String(32), nullable=False, server_default="ACC-DEFAULT"))

    # 2. Forward migration for goal_contributions.user_id
    if "goal_contributions" in tables:
        goal_cols = [c["name"] for c in insp.get_columns("goal_contributions")]
        if "user_id" not in goal_cols:
            with op.batch_alter_table("goal_contributions") as batch_op:
                batch_op.add_column(sa.Column("user_id", sa.String(64), nullable=False, server_default="usr-shivraj-001"))
                batch_op.create_index("ix_goal_contributions_user_id", ["user_id"])

    # 3. Forward migration for ai_conversations.is_deleted
    if "ai_conversations" in tables:
        ai_cols = [c["name"] for c in insp.get_columns("ai_conversations")]
        if "is_deleted" not in ai_cols:
            with op.batch_alter_table("ai_conversations") as batch_op:
                batch_op.add_column(sa.Column("is_deleted", sa.Boolean(), nullable=True, server_default=sa.false()))

    # 4. Forward migration for securities.canonical_id
    if "securities" in tables:
        sec_cols = [c["name"] for c in insp.get_columns("securities")]
        if "canonical_id" not in sec_cols:
            with op.batch_alter_table("securities") as batch_op:
                batch_op.add_column(sa.Column("canonical_id", sa.String(70), nullable=True))
                batch_op.create_unique_constraint("uq_securities_canonical_id", ["canonical_id"])

    # 5. Forward migration for retrieval_events table
    if "retrieval_events" not in tables:
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

    # 6. Forward migration for durable transaction_previews table
    if "transaction_previews" not in tables:
        op.create_table(
            "transaction_previews",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("user_id", sa.String(64), nullable=False),
            sa.Column("file_name", sa.String(255), nullable=False),
            sa.Column("file_hash_sha256", sa.String(64), nullable=False),
            sa.Column("total_rows", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("valid_rows", json_type, nullable=False),
            sa.Column("duplicate_rows", json_type, nullable=False),
            sa.Column("invalid_rows", json_type, nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
            sa.Column("committed_upload_id", sa.String(64), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_transaction_previews_user_id", "transaction_previews", ["user_id"])
        op.create_index("ix_transaction_previews_file_hash", "transaction_previews", ["file_hash_sha256"])

    # 7. Forward migration for alert_events columns
    if "alert_events" in tables:
        evt_cols = [c["name"] for c in insp.get_columns("alert_events")]
        if "event_type" not in evt_cols:
            with op.batch_alter_table("alert_events") as batch_op:
                batch_op.add_column(sa.Column("event_type", sa.String(32), nullable=False, server_default="PRICE_ALERT"))
                batch_op.add_column(sa.Column("symbol", sa.String(20), nullable=True))
                batch_op.add_column(sa.Column("triggered_value", sa.Numeric(14, 4), nullable=False, server_default="0.0000"))
                batch_op.add_column(sa.Column("threshold_value", sa.Numeric(14, 4), nullable=False, server_default="0.0000"))
                batch_op.add_column(sa.Column("title", sa.String(255), nullable=False, server_default="Alert Triggered"))
                batch_op.add_column(sa.Column("message", sa.Text(), nullable=False, server_default=""))
                batch_op.add_column(sa.Column("dedupe_key", sa.String(128), nullable=True))
                batch_op.create_index("ix_alert_events_dedupe_key", ["dedupe_key"])

    # 8. Forward migration for goal_projections columns
    if "goal_projections" in tables:
        proj_cols = [c["name"] for c in insp.get_columns("goal_projections")]
        if "user_id" not in proj_cols:
            with op.batch_alter_table("goal_projections") as batch_op:
                batch_op.add_column(sa.Column("user_id", sa.String(64), nullable=False, server_default="usr-shivraj-001"))
                batch_op.add_column(sa.Column("projected_amount", sa.Numeric(14, 2), nullable=False, server_default="0.00"))
                batch_op.add_column(sa.Column("shortfall_surplus", sa.Numeric(14, 2), nullable=False, server_default="0.00"))
                batch_op.add_column(sa.Column("confidence_interval_low", sa.Numeric(14, 2), nullable=False, server_default="0.00"))
                batch_op.add_column(sa.Column("confidence_interval_high", sa.Numeric(14, 2), nullable=False, server_default="0.00"))
                batch_op.add_column(sa.Column("formula_version", sa.String(16), nullable=False, server_default="v1.0"))
                batch_op.add_column(sa.Column("assumptions_payload", json_type, nullable=False, server_default="{}"))
                batch_op.add_column(sa.Column("created_at", sa.DateTime(timezone=True), nullable=True))
                batch_op.create_index("ix_goal_projections_user_id", ["user_id"])

    # 9. Forward migration for market_quotes columns
    if "market_quotes" in tables:
        mq_cols = [c["name"] for c in insp.get_columns("market_quotes")]
        if "price" not in mq_cols:
            uuid_type = sa.String(36) if bind.dialect.name == "sqlite" else postgresql.UUID(as_uuid=True)
            with op.batch_alter_table("market_quotes") as batch_op:
                batch_op.add_column(sa.Column("security_id", uuid_type, nullable=True))
                batch_op.add_column(sa.Column("price", sa.Numeric(14, 4), nullable=False, server_default="0.0000"))
                batch_op.add_column(sa.Column("change", sa.Numeric(14, 4), nullable=False, server_default="0.0000"))
                batch_op.add_column(sa.Column("change_pct", sa.Numeric(8, 4), nullable=False, server_default="0.0000"))
                batch_op.add_column(sa.Column("previous_close", sa.Numeric(14, 4), nullable=False, server_default="0.0000"))
                batch_op.add_column(sa.Column("currency", sa.String(3), nullable=False, server_default="INR"))
                batch_op.add_column(sa.Column("observed_at", sa.DateTime(timezone=True), nullable=True))
                batch_op.add_column(sa.Column("freshness_status", sa.String(20), nullable=False, server_default="LIVE"))
                batch_op.add_column(sa.Column("served_from_cache", sa.Boolean(), nullable=False, server_default=sa.false()))
                batch_op.add_column(sa.Column("is_delayed", sa.Boolean(), nullable=False, server_default=sa.false()))
                batch_op.add_column(sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=True))

    # 10. Forward migration for market_price_history columns
    if "market_price_history" in tables:
        mph_cols = [c["name"] for c in insp.get_columns("market_price_history")]
        if "trade_date" not in mph_cols:
            with op.batch_alter_table("market_price_history") as batch_op:
                batch_op.add_column(sa.Column("trade_date", sa.Date(), nullable=True))
                batch_op.add_column(sa.Column("adj_close_price", sa.Numeric(14, 4), nullable=False, server_default="0.0000"))
                batch_op.add_column(sa.Column("source", sa.String(50), nullable=False, server_default="NSE_EOD"))
                batch_op.add_column(sa.Column("currency", sa.String(3), nullable=False, server_default="INR"))
                batch_op.add_column(sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=True))

    # 11. Forward migration for document_registry columns
    if "document_registry" in tables:
        dr_cols = [c["name"] for c in insp.get_columns("document_registry")]
        if "publishing_date" not in dr_cols:
            with op.batch_alter_table("document_registry") as batch_op:
                batch_op.add_column(sa.Column("doc_type", sa.String(50), nullable=False, server_default="REGULATION"))
                batch_op.add_column(sa.Column("publishing_date", sa.Date(), nullable=True))
                batch_op.add_column(sa.Column("reporting_period", sa.String(50), nullable=True))
                batch_op.add_column(sa.Column("security_symbol", sa.String(20), nullable=True))
                batch_op.add_column(sa.Column("isin", sa.String(20), nullable=True))
                batch_op.add_column(sa.Column("content_hash", sa.String(64), nullable=False, server_default="sha256-pending"))
                batch_op.add_column(sa.Column("status", sa.String(20), nullable=False, server_default="ACTIVE"))

    # 12. Forward migration for document_chunks columns
    if "document_chunks" in tables:
        dc_cols = [c["name"] for c in insp.get_columns("document_chunks")]
        if "content" not in dc_cols:
            with op.batch_alter_table("document_chunks") as batch_op:
                batch_op.add_column(sa.Column("content", sa.Text(), nullable=False, server_default=""))
                batch_op.add_column(sa.Column("word_count", sa.Integer(), nullable=False, server_default="0"))
                batch_op.add_column(sa.Column("embedding_vector", json_type, nullable=True))
                batch_op.add_column(sa.Column("status", sa.String(20), nullable=False, server_default="ACTIVE"))


def downgrade() -> None:
    op.drop_table("transaction_previews")
    op.drop_table("retrieval_events")
    with op.batch_alter_table("securities") as batch_op:
        batch_op.drop_constraint("uq_securities_canonical_id", type_="unique")
        batch_op.drop_column("canonical_id")
    with op.batch_alter_table("ai_conversations") as batch_op:
        batch_op.drop_column("is_deleted")
    with op.batch_alter_table("goal_contributions") as batch_op:
        batch_op.drop_index("ix_goal_contributions_user_id")
        batch_op.drop_column("user_id")
    with op.batch_alter_table("paper_accounts") as batch_op:
        batch_op.drop_column("account_number")
        batch_op.drop_column("status")
