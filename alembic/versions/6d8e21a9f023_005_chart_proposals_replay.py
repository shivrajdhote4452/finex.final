"""005_chart_proposals_replay.

Revision ID: 6d8e21a9f023
Revises: 5c7e81d9f012
Create Date: 2026-10-18 19:30:00.000000

Adds:
- paper_proposals table for structured bounded paper investment approval
- chart_layouts table for saved multi-chart desktop/mobile arrangements
- chart_drawings table for persistent time/price anchored annotations
- chart_indicator_templates table for user-saved indicator presets
- replay_sessions table for historical simulation clocks and SEBI compliance
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6d8e21a9f023"
down_revision: Union[str, None] = "5c7e81d9f012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Paper Proposals Table
    op.create_table(
        "paper_proposals",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("account_id", sa.String(length=64), nullable=False),
        sa.Column("instruction_text", sa.String(length=1000), nullable=False),
        sa.Column("proposed_allocations", sa.JSON(), nullable=False),
        sa.Column("total_budget", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=10), server_default="INR", nullable=False),
        sa.Column("status", sa.String(length=20), server_default="PROPOSED", nullable=False),
        sa.Column("execution_receipts", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["account_id"], ["paper_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_paper_proposals_user_id", "paper_proposals", ["user_id"], unique=False)
    op.create_index("ix_paper_proposals_account_id", "paper_proposals", ["account_id"], unique=False)

    # 2. Chart Layouts Table
    op.create_table(
        "chart_layouts",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=100), server_default="Default Layout", nullable=False),
        sa.Column("layout_type", sa.String(length=20), server_default="single", nullable=False),
        sa.Column("active_symbols", sa.JSON(), nullable=False),
        sa.Column("timeframes", sa.JSON(), nullable=False),
        sa.Column("sync_crosshair", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("sync_time", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("sync_symbol", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("is_default", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chart_layouts_user_id", "chart_layouts", ["user_id"], unique=False)

    # 3. Chart Drawings Table
    op.create_table(
        "chart_drawings",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("drawing_type", sa.String(length=30), nullable=False),
        sa.Column("coordinates", sa.JSON(), nullable=False),
        sa.Column("properties", sa.JSON(), nullable=False),
        sa.Column("market", sa.String(length=10), server_default="NSE", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chart_drawings_user_id", "chart_drawings", ["user_id"], unique=False)
    op.create_index("ix_chart_drawings_symbol", "chart_drawings", ["symbol"], unique=False)

    # 4. Chart Indicator Templates Table
    op.create_table(
        "chart_indicator_templates",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("indicators_config", sa.JSON(), nullable=False),
        sa.Column("is_default", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chart_indicator_templates_user_id", "chart_indicator_templates", ["user_id"], unique=False)

    # 5. Replay Sessions Table
    op.create_table(
        "replay_sessions",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("session_name", sa.String(length=100), server_default="Historical Replay Session", nullable=False),
        sa.Column("market", sa.String(length=20), server_default="NSE", nullable=False),
        sa.Column("simulated_clock", sa.DateTime(timezone=True), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("speed_multiplier", sa.Numeric(precision=4, scale=2), server_default="1.00", nullable=False),
        sa.Column("status", sa.String(length=20), server_default="ACTIVE", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_replay_sessions_user_id", "replay_sessions", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_table("replay_sessions")
    op.drop_table("chart_indicator_templates")
    op.drop_table("chart_drawings")
    op.drop_table("chart_layouts")
    op.drop_table("paper_proposals")
