"""add server defaults to user columns

Revision ID: ce36dbe6c6b8
Revises: 34c249782d33
Create Date: 2026-05-02 16:02:54.187560

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ce36dbe6c6b8'
down_revision: Union[str, Sequence[str], None] = '34c249782d33'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('users', 'role', server_default='user',
                    existing_type=sa.Enum('admin', 'user', name='userrole'), existing_nullable=False)
    op.alter_column('users', 'type', server_default='trainee',
                    existing_type=sa.Enum('trainer', 'trainee', name='usertype'), existing_nullable=False)
    op.alter_column('users', 'gender', server_default='others',
                    existing_type=sa.Enum('male', 'female', 'others', name='usergender'), existing_nullable=False)
    op.alter_column('users', 'email_verified', server_default=sa.text('false'),
                    existing_type=sa.Boolean(), existing_nullable=False)


def downgrade() -> None:
    op.alter_column('users', 'role', server_default=None,
                    existing_type=sa.Enum('admin', 'user', name='userrole'), existing_nullable=False)
    op.alter_column('users', 'type', server_default=None,
                    existing_type=sa.Enum('trainer', 'trainee', name='usertype'), existing_nullable=False)
    op.alter_column('users', 'gender', server_default=None,
                    existing_type=sa.Enum('male', 'female', 'others', name='usergender'), existing_nullable=False)
    op.alter_column('users', 'email_verified', server_default=None,
                    existing_type=sa.Boolean(), existing_nullable=False)
