"""is_active server default false

Revision ID: f1a3d9e2b805
Revises: 3bdc41c3508a
Create Date: 2026-05-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f1a3d9e2b805'
down_revision: Union[str, Sequence[str], None] = '3bdc41c3508a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        'users',
        'is_active',
        server_default=sa.text('false'),
        existing_type=sa.Boolean(),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        'users',
        'is_active',
        server_default=None,
        existing_type=sa.Boolean(),
        existing_nullable=False,
    )
