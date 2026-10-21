"""006_market_and_proposal_compatibility.

Revision ID: 7e9f32b0a134
Revises: 6d8e21a9f023
Create Date: 2026-10-19 00:25:00.000000

Adds missing ORM compatibility columns with safe non-destructive backfills:
- securities: provider_token (index)
- market_quotes: symbol (index), close_price
- market_price_history: symbol (index), interval, observed_at (index)
- paper_proposals: conversation_id (index), requested_budget
"""

from typing import Sequence, Union
import sqlalchemy as sa
from alembic import context as alembic_context
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7e9f32b0a134"
down_revision: Union[str, None] = "6d8e21a9f023"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    is_sqlite = conn.dialect.name == "sqlite"
    # Offline (--sql) mode has no live DB: MockConnection cannot be inspected.
    # Assume nothing exists so all DDL is emitted; online behavior unchanged.
    inspector = None if alembic_context.is_offline_mode() else sa.inspect(conn)

    def get_column_names(table_name: str) -> set:
        if inspector is None:
            return set()
        return {col["name"] for col in inspector.get_columns(table_name)}

    def get_index_names(table_name: str) -> set:
        if inspector is None:
            return set()
        return {idx["name"] for idx in inspector.get_indexes(table_name)}

    # 1. securities.provider_token
    sec_cols = get_column_names("securities")
    sec_indexes = get_index_names("securities")
    if "provider_token" not in sec_cols:
        op.add_column("securities", sa.Column("provider_token", sa.String(length=32), nullable=True))
    if "ix_securities_provider_token" not in sec_indexes:
        op.create_index("ix_securities_provider_token", "securities", ["provider_token"], unique=False)

    # 2. market_quotes: symbol, close_price
    mq_cols = get_column_names("market_quotes")
    mq_indexes = get_index_names("market_quotes")
    if "symbol" not in mq_cols:
        op.add_column("market_quotes", sa.Column("symbol", sa.String(length=32), nullable=True))
    else:
        if not is_sqlite:
            op.alter_column(
                "market_quotes",
                "symbol",
                type_=sa.String(length=32),
                existing_type=sa.String(length=20),
                existing_nullable=True,
            )
    if "close_price" not in mq_cols:
        op.add_column("market_quotes", sa.Column("close_price", sa.Numeric(precision=18, scale=4), nullable=True))
    if "ix_market_quotes_symbol" not in mq_indexes:
        op.create_index("ix_market_quotes_symbol", "market_quotes", ["symbol"], unique=False)

    # 3. market_price_history: symbol, interval, observed_at
    mph_cols = get_column_names("market_price_history")
    mph_indexes = get_index_names("market_price_history")
    if "symbol" not in mph_cols:
        op.add_column("market_price_history", sa.Column("symbol", sa.String(length=32), nullable=True))
    if "interval" not in mph_cols:
        op.add_column(
            "market_price_history", sa.Column("interval", sa.String(length=32), server_default="1D", nullable=True)
        )
    if "observed_at" not in mph_cols:
        op.add_column("market_price_history", sa.Column("observed_at", sa.DateTime(timezone=True), nullable=True))
    if "ix_market_price_history_symbol" not in mph_indexes:
        op.create_index("ix_market_price_history_symbol", "market_price_history", ["symbol"], unique=False)
    if "ix_market_price_history_observed_at" not in mph_indexes:
        op.create_index("ix_market_price_history_observed_at", "market_price_history", ["observed_at"], unique=False)

    # 4. paper_proposals: conversation_id, requested_budget
    pp_cols = get_column_names("paper_proposals")
    pp_indexes = get_index_names("paper_proposals")
    if "conversation_id" not in pp_cols:
        op.add_column("paper_proposals", sa.Column("conversation_id", sa.String(length=64), nullable=True))
    if "requested_budget" not in pp_cols:
        op.add_column(
            "paper_proposals", sa.Column("requested_budget", sa.Numeric(precision=14, scale=2), nullable=True)
        )
    if "ix_paper_proposals_conversation_id" not in pp_indexes:
        op.create_index("ix_paper_proposals_conversation_id", "paper_proposals", ["conversation_id"], unique=False)

    # --- Safe Non-Destructive Backfills ---
    if is_sqlite:
        conn.execute(
            sa.text("""
            UPDATE market_quotes
            SET symbol = (SELECT s.symbol FROM securities s WHERE s.id = market_quotes.security_id)
            WHERE symbol IS NULL;
        """)
        )
        conn.execute(
            sa.text("""
            UPDATE market_quotes
            SET close_price = price
            WHERE close_price IS NULL;
        """)
        )
        conn.execute(
            sa.text("""
            UPDATE market_price_history
            SET symbol = (SELECT s.symbol FROM securities s WHERE s.id = market_price_history.security_id)
            WHERE symbol IS NULL;
        """)
        )
        conn.execute(
            sa.text("""
            UPDATE market_price_history
            SET interval = '1D'
            WHERE interval IS NULL;
        """)
        )
        conn.execute(
            sa.text("""
            UPDATE paper_proposals
            SET requested_budget = total_budget
            WHERE requested_budget IS NULL;
        """)
        )
    else:
        # PostgreSQL backfills
        conn.execute(
            sa.text("""
            UPDATE market_quotes mq
            SET symbol = s.symbol
            FROM securities s
            WHERE mq.security_id = s.id AND mq.symbol IS NULL;
        """)
        )
        conn.execute(
            sa.text("""
            UPDATE market_quotes
            SET close_price = price
            WHERE close_price IS NULL;
        """)
        )
        conn.execute(
            sa.text("""
            UPDATE market_price_history mph
            SET symbol = s.symbol
            FROM securities s
            WHERE mph.security_id = s.id AND mph.symbol IS NULL;
        """)
        )
        conn.execute(
            sa.text("""
            UPDATE market_price_history
            SET interval = '1D'
            WHERE interval IS NULL;
        """)
        )
        conn.execute(
            sa.text("""
            UPDATE market_price_history
            SET observed_at = trade_date::timestamp with time zone
            WHERE observed_at IS NULL;
        """)
        )
        conn.execute(
            sa.text("""
            UPDATE paper_proposals
            SET requested_budget = total_budget
            WHERE requested_budget IS NULL;
        """)
        )


def downgrade() -> None:
    # 4. paper_proposals
    op.drop_index("ix_paper_proposals_conversation_id", table_name="paper_proposals")
    op.drop_column("paper_proposals", "requested_budget")
    op.drop_column("paper_proposals", "conversation_id")

    # 3. market_price_history
    op.drop_index("ix_market_price_history_observed_at", table_name="market_price_history")
    op.drop_index("ix_market_price_history_symbol", table_name="market_price_history")
    op.drop_column("market_price_history", "observed_at")
    op.drop_column("market_price_history", "interval")
    op.drop_column("market_price_history", "symbol")

    # 2. market_quotes
    op.drop_index("ix_market_quotes_symbol", table_name="market_quotes")
    op.drop_column("market_quotes", "close_price")
    op.drop_column("market_quotes", "symbol")

    # 1. securities
    op.drop_index("ix_securities_provider_token", table_name="securities")
    op.drop_column("securities", "provider_token")
