"""Merge branches

Revision ID: 7c91733271fd
Revises: ffc55af2be47, 691171bbcd12
Create Date: 2026-04-11 17:25:13.842226

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7c91733271fd'
down_revision: Union[str, Sequence[str], None] = ('ffc55af2be47', '691171bbcd12')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
