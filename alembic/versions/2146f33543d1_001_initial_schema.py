"""001_initial_schema

Revision ID: 2146f33543d1
Revises:
Create Date: 2026-10-16 22:02:37.969925
"""

from typing import Sequence, Union

from alembic import op
from backend.app.models import Base

# revision identifiers, used by Alembic.
revision: str = "2146f33543d1"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all operational database entities declared across all domains."""
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    """Drop all operational database entities."""
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
