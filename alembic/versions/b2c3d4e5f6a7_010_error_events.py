"""010_error_events.

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-11-23 20:30:00.000000

Creates error_events table for durable, bounded operational error tracking and observability.
"""

from typing import Sequence, Union
import sqlalchemy as sa
from alembic import context as alembic_context
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = None if alembic_context.is_offline_mode() else sa.inspect(conn)

    def table_exists(table_name: str) -> bool:
        if inspector is None:
            return False
        return table_name in inspector.get_table_names()

    if not table_exists("error_events"):
        op.create_table(
            "error_events",
            sa.Column("id", sa.String(length=64), primary_key=True),
            sa.Column("correlation_id", sa.String(length=100), nullable=True),
            sa.Column("endpoint", sa.String(length=255), nullable=False),
            sa.Column("method", sa.String(length=10), nullable=False),
            sa.Column("status_code", sa.Integer(), nullable=False),
            sa.Column("error_type", sa.String(length=100), nullable=False),
            sa.Column("category", sa.String(length=50), nullable=False),
            sa.Column("feature_area", sa.String(length=50), nullable=False),
            sa.Column("sanitized_message", sa.Text(), nullable=False),
            sa.Column("user_id", sa.String(length=64), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
        )
        try:
            op.create_index("ix_error_events_created_at", "error_events", ["created_at"])
            op.create_index("ix_error_events_correlation_id", "error_events", ["correlation_id"])
            op.create_index("ix_error_events_status_code", "error_events", ["status_code"])
            op.create_index("ix_error_events_category", "error_events", ["category"])
            op.create_index("ix_error_events_feature_area", "error_events", ["feature_area"])
            op.create_index("ix_error_events_endpoint", "error_events", ["endpoint"])
            op.create_index("ix_error_events_error_type", "error_events", ["error_type"])
            op.create_index("ix_error_events_user_id", "error_events", ["user_id"])
        except Exception:
            pass


def downgrade() -> None:
    conn = op.get_bind()
    inspector = None if alembic_context.is_offline_mode() else sa.inspect(conn)

    def table_exists(table_name: str) -> bool:
        if inspector is None:
            return True
        return table_name in inspector.get_table_names()

    if table_exists("error_events"):
        op.drop_table("error_events")
