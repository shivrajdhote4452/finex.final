"""003_risk_profile_and_revocation

Revision ID: 4b6f23a8c7e5
Revises: 3a5e12f9b8c4
Create Date: 2026-10-18 02:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import context, op

revision: str = "4b6f23a8c7e5"
down_revision: Union[str, Sequence[str], None] = "3a5e12f9b8c4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

json_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    if context.is_offline_mode():
        op.add_column("user_profiles", sa.Column("risk_band", sa.String(50), nullable=True))
        op.add_column("user_profiles", sa.Column("composite_score", sa.Numeric(5, 2), nullable=True))
        op.add_column("user_profiles", sa.Column("risk_assessment", json_type, nullable=True))
        op.create_table(
            "revoked_tokens",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("token", sa.String(512), nullable=False, unique=True),
            sa.Column("user_id", sa.String(64), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_revoked_tokens_token", "revoked_tokens", ["token"])
        op.create_index("ix_revoked_tokens_user_id", "revoked_tokens", ["user_id"])
        return

    from sqlalchemy import inspect

    bind = op.get_bind()
    insp = inspect(bind)

    # 1. Forward migration for user_profiles risk fields
    profile_cols = [c["name"] for c in insp.get_columns("user_profiles")]
    if "risk_band" not in profile_cols:
        op.add_column("user_profiles", sa.Column("risk_band", sa.String(50), nullable=True))
    if "composite_score" not in profile_cols:
        op.add_column("user_profiles", sa.Column("composite_score", sa.Numeric(5, 2), nullable=True))
    if "risk_assessment" not in profile_cols:
        op.add_column("user_profiles", sa.Column("risk_assessment", json_type, nullable=True))

    # 2. Forward migration for revoked_tokens table
    tables = insp.get_table_names()
    if "revoked_tokens" not in tables:
        op.create_table(
            "revoked_tokens",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("token", sa.String(512), nullable=False, unique=True),
            sa.Column("user_id", sa.String(64), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_revoked_tokens_token", "revoked_tokens", ["token"])
        op.create_index("ix_revoked_tokens_user_id", "revoked_tokens", ["user_id"])


def downgrade() -> None:
    op.drop_table("revoked_tokens")
    with op.batch_alter_table("user_profiles") as batch_op:
        batch_op.drop_column("risk_assessment")
        batch_op.drop_column("composite_score")
        batch_op.drop_column("risk_band")
