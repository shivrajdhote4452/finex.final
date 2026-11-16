"""009_email_password_auth_and_tokens.

Revision ID: a1b2c3d4e5f6
Revises: 9b3a64c2d458
Create Date: 2026-11-16 12:00:00.000000

Adds password_hash, email_verified, and google_subject to users table,
and creates auth_tokens table for email verification and password reset.
"""

from typing import Sequence, Union
import sqlalchemy as sa
from alembic import context as alembic_context
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "9b3a64c2d458"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = None if alembic_context.is_offline_mode() else sa.inspect(conn)

    def table_exists(table_name: str) -> bool:
        if inspector is None:
            return False
        return table_name in inspector.get_table_names()

    def column_names(table_name: str) -> set:
        if inspector is None:
            return set()
        return {col["name"] for col in inspector.get_columns(table_name)}

    # 1. Add columns to users table if not present
    if table_exists("users"):
        existing_cols = column_names("users")

        if "password_hash" not in existing_cols:
            op.add_column("users", sa.Column("password_hash", sa.String(length=255), nullable=True))

        if "email_verified" not in existing_cols:
            op.add_column(
                "users",
                sa.Column("email_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            )

        if "google_subject" not in existing_cols:
            op.add_column("users", sa.Column("google_subject", sa.String(length=255), nullable=True))
            try:
                op.create_index("ix_users_google_subject", "users", ["google_subject"], unique=True)
            except Exception:
                pass

        # Backfill existing Google users: mark verified and set google_subject
        try:
            op.execute(
                sa.text(
                    "UPDATE users SET google_subject = provider_subject, email_verified = true "
                    "WHERE provider = 'google' AND google_subject IS NULL"
                )
            )
            op.execute(
                sa.text(
                    "UPDATE users SET email_verified = true WHERE is_verified = true"
                )
            )
        except Exception:
            pass

    # 2. Create auth_tokens table if not exists
    if not table_exists("auth_tokens"):
        op.create_table(
            "auth_tokens",
            sa.Column("id", sa.String(length=64), nullable=False),
            sa.Column("user_id", sa.String(length=64), nullable=False),
            sa.Column("token_hash", sa.String(length=64), nullable=False),
            sa.Column("token_type", sa.String(length=32), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        try:
            op.create_index("ix_auth_tokens_token_hash", "auth_tokens", ["token_hash"], unique=True)
            op.create_index("ix_auth_tokens_user_id", "auth_tokens", ["user_id"], unique=False)
            op.create_index("ix_auth_tokens_expires_at", "auth_tokens", ["expires_at"], unique=False)
        except Exception:
            pass


def downgrade() -> None:
    conn = op.get_bind()
    inspector = None if alembic_context.is_offline_mode() else sa.inspect(conn)

    def table_exists(table_name: str) -> bool:
        if inspector is None:
            return False
        return table_name in inspector.get_table_names()

    if table_exists("auth_tokens"):
        op.drop_table("auth_tokens")

    if table_exists("users"):
        existing_cols = {col["name"] for col in inspector.get_columns("users")}
        if "google_subject" in existing_cols:
            try:
                op.drop_index("ix_users_google_subject", table_name="users")
            except Exception:
                pass
            op.drop_column("users", "google_subject")
        if "email_verified" in existing_cols:
            op.drop_column("users", "email_verified")
        if "password_hash" in existing_cols:
            op.drop_column("users", "password_hash")
