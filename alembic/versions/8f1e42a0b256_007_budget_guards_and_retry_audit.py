"""007_budget_guards_and_retry_audit.

Revision ID: 8f1e42a0b256
Revises: 7e9f32b0a134
Create Date: 2026-10-19 12:30:00.000000

Forward migration ensuring:
- paper_proposals.attempt_count (indexed)
- Verification of schema consistency across clean and upgraded databases
"""

from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8f1e42a0b256"
down_revision: Union[str, None] = "7e9f32b0a134"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    def get_column_names(table_name: str) -> set:
        return {col["name"] for col in inspector.get_columns(table_name)}

    def get_index_names(table_name: str) -> set:
        return {idx["name"] for idx in inspector.get_indexes(table_name)}

    # 1. paper_proposals: attempt_count
    pp_cols = get_column_names("paper_proposals")
    pp_indexes = get_index_names("paper_proposals")
    if "attempt_count" not in pp_cols:
        op.add_column(
            "paper_proposals",
            sa.Column("attempt_count", sa.Integer(), server_default="1", nullable=False),
        )
    if "ix_paper_proposals_attempt_count" not in pp_indexes:
        op.create_index("ix_paper_proposals_attempt_count", "paper_proposals", ["attempt_count"], unique=False)

    # Backfill attempt_count for any existing rows
    conn.execute(sa.text("""
        UPDATE paper_proposals
        SET attempt_count = 1
        WHERE attempt_count IS NULL;
    """))


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    def get_index_names(table_name: str) -> set:
        return {idx["name"] for idx in inspector.get_indexes(table_name)}

    def get_column_names(table_name: str) -> set:
        return {col["name"] for col in inspector.get_columns(table_name)}

    pp_indexes = get_index_names("paper_proposals")
    pp_cols = get_column_names("paper_proposals")

    if "ix_paper_proposals_attempt_count" in pp_indexes:
        op.drop_index("ix_paper_proposals_attempt_count", table_name="paper_proposals")
    if "attempt_count" in pp_cols:
        op.drop_column("paper_proposals", "attempt_count")
