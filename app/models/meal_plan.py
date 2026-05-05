"""
Meal Plan database models
"""
from sqlalchemy import (
    Column, String, Integer, Float, DateTime, Date, Boolean,
    ForeignKey, Text, Enum, Index
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
import enum

from app.database import Base


# ============================================================================
# ENUMS
# ============================================================================


class MealCategory(enum.Enum):
    """Category for a meal/food item in the library"""
    breakfast = "breakfast"
    lunch = "lunch"
    dinner = "dinner"
    snack = "snack"
    drink = "drink"
    dessert = "dessert"
    other = "other"


class MealType(enum.Enum):
    """Which slot of the day a meal is planned for"""
    breakfast = "breakfast"
    lunch = "lunch"
    dinner = "dinner"
    snack = "snack"


# ============================================================================
# MEAL PLAN MODELS
# ============================================================================


class Meals(Base):
    """
    Meals model - Library of available meals/foods that users can pick from.
    Think of this as the food database (like MyFitnessPal's food library).
    """
    __tablename__ = "meals"
    __table_args__ = (
        Index("ix_meals_name_is_custom", "name", "is_custom"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)  # type: ignore
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    category = Column(Enum(MealCategory), default=MealCategory.other, nullable=False)  # type: ignore

    # Nutritional info per serving
    calories = Column(Integer, nullable=False, default=0)
    protein_grams = Column(Float, nullable=True, default=0)
    carbs_grams = Column(Float, nullable=True, default=0)
    fat_grams = Column(Float, nullable=True, default=0)
    fiber_grams = Column(Float, nullable=True, default=0)
    serving_size = Column(String(100), nullable=True)  # e.g. "1 cup", "100g", "1 piece"

    image_url = Column(String(512), nullable=True)
    is_custom = Column(Boolean, default=False, nullable=False)  # user-created vs system meal
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)  # type: ignore

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)  # For soft deletes

    # Relationships
    creator = relationship("User", backref="created_meals")
    meal_plan_items = relationship("Meal_Plan_Items", back_populates="meal")
    serving_unit_id = Column(UUID(as_uuid=True), ForeignKey("serving_units.id"), nullable=True)  # type: ignore
    serving_unit = relationship("Serving_Units")

    def __repr__(self):
        return f"<Meal {self.name} ({self.calories} cal)>"


class Meal_Plans(Base):
    """
    Meal Plans model - A user's daily plan or a reusable template.
    Daily plans are one per user per date (enforced in migration).
    """
    __tablename__ = "meal_plans"
    __table_args__ = (
        Index("ix_meal_plans_template_name", "template_name"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)  # type: ignore
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)  # type: ignore

    date = Column(Date, nullable=True)  # Null for templates
    notes = Column(Text, nullable=True)
    target_calories = Column(Integer, nullable=True)
    template_name = Column(String(255), nullable=True)
    is_template = Column(Boolean, default=False, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="meal_plans")
    items = relationship("Meal_Plan_Items", back_populates="meal_plan", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<MealPlan user={self.user_id} date={self.date} is_template={self.is_template}>"


class Meal_Plan_Items(Base):
    """
    Meal Plan Items model - Individual meals chosen for a specific slot in a daily plan.
    Links a meal from the library to a user's daily meal plan with a time slot and serving count.
    """
    __tablename__ = "meal_plan_items"
    __table_args__ = (
        Index("ix_meal_plan_items_plan_id_type", "meal_plan_id", "meal_type"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)  # type: ignore
    meal_plan_id = Column(UUID(as_uuid=True), ForeignKey("meal_plans.id", ondelete="CASCADE"), nullable=False)  # type: ignore
    meal_id = Column(UUID(as_uuid=True), ForeignKey("meals.id"), nullable=False)  # type: ignore
    meal_type = Column(Enum(MealType), nullable=False)  # type: ignore
    servings = Column(Float, default=1.0, nullable=False)
    order_index = Column(Integer, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    meal_plan = relationship("Meal_Plans", back_populates="items")
    meal = relationship("Meals", back_populates="meal_plan_items")

    def __repr__(self):
        return f"<MealPlanItem plan={self.meal_plan_id} meal={self.meal_id} type={self.meal_type}>"


class Serving_Units(Base):
    """
    Serving Units model - Defines standard units for meal servings (e.g., gram, cup, oz).
    """
    __tablename__ = "serving_units"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)  # type: ignore
    name = Column(String(50), nullable=False, unique=True)
    description = Column(String(255), nullable=True)

    def __repr__(self):
        return f"<ServingUnit {self.name}>"