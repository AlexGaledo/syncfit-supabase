"""merge heads

Revision ID: f813e9a470bc
Revises: 0196d4a6ee4c, 186ec409e823
Create Date: 2026-04-13 20:31:53.100114

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f813e9a470bc'
down_revision: Union[str, Sequence[str], None] = ('0196d4a6ee4c', '186ec409e823')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = ('0196d4a6ee4c', '186ec409e823')


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
