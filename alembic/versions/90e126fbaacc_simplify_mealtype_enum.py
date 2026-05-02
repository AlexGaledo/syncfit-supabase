"""Simplify mealtype enum

Revision ID: 90e126fbaacc
Revises: ce36dbe6c6b8
Create Date: 2026-05-02 21:10:27.438684

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "90e126fbaacc"
down_revision: Union[str, Sequence[str], None] = "ce36dbe6c6b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade():
    # 1) Rename old enum
    op.execute("ALTER TYPE mealtype RENAME TO mealtype_old")

    # 2) Create new 4-slot enum
    new_enum = postgresql.ENUM('breakfast', 'lunch', 'dinner', 'snack', name='mealtype')
    new_enum.create(op.get_bind(), checkfirst=False)

    # 3) Alter column + map old snacks -> snack
    op.execute("""
        ALTER TABLE meal_plan_items 
        ALTER COLUMN meal_type TYPE mealtype 
        USING CASE 
            WHEN meal_type::text IN ('morning_snack','afternoon_snack','evening_snack') THEN 'snack'::mealtype
            ELSE meal_type::text::mealtype
        END
    """)

    # 4) Drop old enum
    op.execute("DROP TYPE mealtype_old")


def downgrade():
    # 1) Rename current enum
    op.execute("ALTER TYPE mealtype RENAME TO mealtype_new")

    # 2) Recreate old 6-slot enum
    old_enum = postgresql.ENUM(
        'breakfast', 'morning_snack', 'lunch',
        'afternoon_snack', 'dinner', 'evening_snack',
        name='mealtype'
    )
    old_enum.create(op.get_bind(), checkfirst=False)

    # 3) Alter column back (snack -> afternoon_snack fallback)
    op.execute("""
        ALTER TABLE meal_plan_items 
        ALTER COLUMN meal_type TYPE mealtype 
        USING CASE 
            WHEN meal_type::text = 'snack' THEN 'afternoon_snack'::mealtype
            ELSE meal_type::text::mealtype
        END
    """)

    # 4) Drop temp enum
    op.execute("DROP TYPE mealtype_new")