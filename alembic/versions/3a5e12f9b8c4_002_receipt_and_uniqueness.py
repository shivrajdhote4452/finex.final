"""002_receipt_and_uniqueness

Revision ID: 3a5e12f9b8c4
Revises: 2146f33543d1
Create Date: 2026-10-16 23:36:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "3a5e12f9b8c4"
down_revision: Union[str, Sequence[str], None] = "2146f33543d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from alembic import context
    if context.is_offline_mode():
        op.add_column("paper_orders", sa.Column("execution_receipt", sa.JSON(), nullable=True))
        with op.batch_alter_table("transaction_uploads") as batch_op:
            batch_op.create_unique_constraint("uq_upload_user_file_hash", ["user_id", "file_hash_sha256"])
        with op.batch_alter_table("transactions") as batch_op:
            batch_op.create_unique_constraint("uq_transaction_user_dedupe", ["user_id", "dedupe_hash"])
        return

    # 1. Add execution_receipt column to paper_orders for idempotent replay if not present
    from sqlalchemy import inspect
    bind = op.get_bind()
    insp = inspect(bind)
    cols = [c["name"] for c in insp.get_columns("paper_orders")]
    if "execution_receipt" not in cols:
        op.add_column("paper_orders", sa.Column("execution_receipt", sa.JSON(), nullable=True))

    # 2. Add uniqueness constraints on transaction uploads and transactions if not present
    uq_uploads = [u["name"] for u in insp.get_unique_constraints("transaction_uploads")]
    if "uq_upload_user_file_hash" not in uq_uploads:
        with op.batch_alter_table("transaction_uploads") as batch_op:
            batch_op.create_unique_constraint("uq_upload_user_file_hash", ["user_id", "file_hash_sha256"])

    uq_txs = [u["name"] for u in insp.get_unique_constraints("transactions")]
    if "uq_transaction_user_dedupe" not in uq_txs:
        with op.batch_alter_table("transactions") as batch_op:
            batch_op.create_unique_constraint("uq_transaction_user_dedupe", ["user_id", "dedupe_hash"])


def downgrade() -> None:
    with op.batch_alter_table("transactions") as batch_op:
        batch_op.drop_constraint("uq_transaction_user_dedupe", type_="unique")
    with op.batch_alter_table("transaction_uploads") as batch_op:
        batch_op.drop_constraint("uq_upload_user_file_hash", type_="unique")
    op.drop_column("paper_orders", "execution_receipt")
