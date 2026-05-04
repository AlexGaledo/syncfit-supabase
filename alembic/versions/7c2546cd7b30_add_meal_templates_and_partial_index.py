"""add_meal_templates_and_partial_index

Revision ID: 7c2546cd7b30
Revises: 90e126fbaacc
Create Date: 2026-05-05 01:56:37.759544

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7c2546cd7b30'
down_revision: Union[str, Sequence[str], None] = '90e126fbaacc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column(
        "meal_plans",
        sa.Column("is_template", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.alter_column("meal_plans", "date", existing_type=sa.Date(), nullable=True)
    op.drop_constraint("uq_meal_plans_user_id_date", "meal_plans", type_="unique")
    op.create_index(
        "ix_meal_plans_user_date_unique",
        "meal_plans",
        ["user_id", "date"],
        unique=True,
        postgresql_where=sa.text("is_template = false AND date IS NOT NULL"),
    )
    op.alter_column("meal_plans", "is_template", server_default=None)
    # ### end Alembic commands ###


def downgrade():
    op.drop_index("ix_meal_plans_user_date_unique", table_name="meal_plans")
    op.create_unique_constraint("uq_meal_plans_user_id_date", "meal_plans", ["user_id", "date"])
    op.alter_column("meal_plans", "date", existing_type=sa.Date(), nullable=False)
    op.drop_column("meal_plans", "is_template")
    # ### end Alembic commands ###
