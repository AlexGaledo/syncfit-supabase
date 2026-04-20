"""merge heads

Revision ID: 62a10597fab9
Revises: b74e7b55146b, 422293052c66
Create Date: 2026-04-18 19:27:12.471773

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '62a10597fab9'
down_revision: Union[str, Sequence[str], None] = ('b74e7b55146b', '422293052c66')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
