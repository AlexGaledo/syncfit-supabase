"""add macro targets to meal plans and templates

Revision ID: e10327c87ca3
Revises: 7c2546cd7b30
Create Date: 2026-05-08 02:32:13.844618

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e10327c87ca3'
down_revision: Union[str, Sequence[str], None] = '7c2546cd7b30'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add target macro columns to meal_plans
    op.add_column('meal_plans', sa.Column('target_protein_grams', sa.Float(), nullable=True))
    op.add_column('meal_plans', sa.Column('target_carbs_grams', sa.Float(), nullable=True))
    op.add_column('meal_plans', sa.Column('target_fat_grams', sa.Float(), nullable=True))
    
    # Add profile macro columns to user_profiles
    op.add_column('user_profiles', sa.Column('macro_protein_pct', sa.Integer(), nullable=True))
    op.add_column('user_profiles', sa.Column('macro_carb_pct', sa.Integer(), nullable=True))
    op.add_column('user_profiles', sa.Column('macro_fat_pct', sa.Integer(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove profile macro columns from user_profiles
    op.drop_column('user_profiles', 'macro_fat_pct')
    op.drop_column('user_profiles', 'macro_carb_pct')
    op.drop_column('user_profiles', 'macro_protein_pct')
    
    # Remove target macro columns from meal_plans
    op.drop_column('meal_plans', 'target_fat_grams')
    op.drop_column('meal_plans', 'target_carbs_grams')
    op.drop_column('meal_plans', 'target_protein_grams')