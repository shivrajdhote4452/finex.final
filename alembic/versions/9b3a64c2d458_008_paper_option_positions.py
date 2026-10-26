"""008_paper_option_positions.

Revision ID: 9b3a64c2d458
Revises: 8f1e42a0b256
Create Date: 2026-10-26 12:00:00.000000

Phase 2: Creates paper_option_positions table for isolated options trading holdings.
"""

from typing import Sequence, Union
import sqlalchemy as sa
from alembic import context as alembic_context
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9b3a64c2d458"
down_revision: Union[str, None] = "8f1e42a0b256"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = None if alembic_context.is_offline_mode() else sa.inspect(conn)

    def table_exists(table_name: str) -> bool:
        if inspector is None:
            return False
        return table_name in inspector.get_table_names()

    if not table_exists("paper_option_positions"):
        op.create_table(
            "paper_option_positions",
            sa.Column("id", sa.String(length=64), nullable=False),
            sa.Column("account_id", sa.String(length=64), nullable=False),
            sa.Column("contract_symbol", sa.String(length=64), nullable=False),
            sa.Column("underlying", sa.String(length=30), nullable=False),
            sa.Column("option_type", sa.String(length=5), nullable=False),
            sa.Column("strike", sa.Numeric(precision=14, scale=2), nullable=False),
            sa.Column("expiry", sa.String(length=20), nullable=False),
            sa.Column("lots", sa.Integer(), nullable=False),
            sa.Column("lot_size", sa.Integer(), nullable=False),
            sa.Column("total_quantity", sa.Integer(), nullable=False),
            sa.Column("average_premium", sa.Numeric(precision=14, scale=2), nullable=False),
            sa.Column("total_cost_basis", sa.Numeric(precision=14, scale=2), nullable=False),
            sa.Column("breakeven", sa.Numeric(precision=14, scale=2), nullable=False),
            sa.Column("max_loss", sa.Numeric(precision=14, scale=2), nullable=False),
            sa.Column("status", sa.String(length=20), server_default="OPEN", nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["account_id"], ["paper_accounts.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("account_id", "contract_symbol", name="uq_paper_option_position_contract"),
        )


def downgrade() -> None:
    op.drop_table("paper_option_positions")
