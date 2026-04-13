"""Merge meal plan and other feature branches

Revision ID: 0196d4a6ee4c
Revises: 1a4d6f8c9b20, 691171bbcd12
Create Date: 2026-04-13 18:15:36.780550

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0196d4a6ee4c'
down_revision: Union[str, Sequence[str], None] = ('1a4d6f8c9b20', '691171bbcd12')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
