"""
Meal Plan schemas for request/response validation
"""
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import datetime, date
from uuid import UUID
from enum import Enum


# ============================================================================
# ENUMS
# ============================================================================

class MealCategory(str, Enum):
    breakfast = "breakfast"
    lunch = "lunch"
    dinner = "dinner"
    snack = "snack"
    drink = "drink"
    dessert = "dessert"
    other = "other"


class MealType(str, Enum):
    breakfast = "breakfast"
    lunch = "lunch"
    dinner = "dinner"
    snack = "snack"


# ============================================================================
# MEALS (FOOD LIBRARY) SCHEMAS
# ============================================================================

class MealBase(BaseModel):
    """Base meal schema - represents a food/meal in the library"""
    name: str
    description: Optional[str] = None
    category: MealCategory = MealCategory.other
    calories: int = Field(default=0, ge=0)
    protein_grams: Optional[float] = Field(default=0, ge=0)
    carbs_grams: Optional[float] = Field(default=0, ge=0)
    fat_grams: Optional[float] = Field(default=0, ge=0)
    fiber_grams: Optional[float] = Field(default=0, ge=0)
    serving_size: Optional[str] = None  # e.g. "1 cup", "100g"
    image_url: Optional[str] = None


class MealCreate(MealBase):
    """Schema for creating a meal in the food library"""
    is_custom: bool = False
    created_by: Optional[UUID] = None


class MealUpdate(BaseModel):
    """Schema for updating a meal"""
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[MealCategory] = None
    calories: Optional[int] = Field(default=None, ge=0)
    protein_grams: Optional[float] = Field(default=None, ge=0)
    carbs_grams: Optional[float] = Field(default=None, ge=0)
    fat_grams: Optional[float] = Field(default=None, ge=0)
    fiber_grams: Optional[float] = Field(default=None, ge=0)
    serving_size: Optional[str] = None
    image_url: Optional[str] = None


class MealResponse(MealBase):
    """Schema for meal response"""
    id: UUID
    is_custom: bool
    created_by: Optional[UUID] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# MEAL PLANS (DAILY PLAN) SCHEMAS
# ============================================================================

class MealPlanBase(BaseModel):
    """Base meal plan schema - a user's daily meal plan"""
    date: date
    notes: Optional[str] = None
    target_calories: Optional[int] = Field(default=None, ge=0)


class MealPlanCreate(MealPlanBase):
    """Schema for creating a daily meal plan, with an optional template."""
    template_name: Optional[str] = None


class MealPlanUpdate(BaseModel):
    """Schema for updating a meal plan"""
    notes: Optional[str] = None
    target_calories: Optional[int] = Field(default=None, ge=0)


class MealPlanResponse(MealPlanBase):
    """Schema for meal plan response (without items)"""
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class MealPlanDetailResponse(MealPlanResponse):
    """Schema for meal plan response with nested items"""
    items: List["MealPlanItemResponse"] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# MEAL PLAN ITEMS SCHEMAS
# ============================================================================

class MealPlanItemBase(BaseModel):
    """Base meal plan item schema - a single meal in a daily plan slot"""
    meal_id: UUID
    meal_type: MealType
    servings: float = Field(default=1.0, gt=0)
    order_index: Optional[int] = None


class MealPlanItemCreate(MealPlanItemBase):
    """Schema for adding a meal to a daily plan"""
    pass


class MealPlanItemUpdate(BaseModel):
    """Schema for updating a meal plan item"""
    meal_type: Optional[MealType] = None
    servings: Optional[float] = Field(default=None, gt=0)
    order_index: Optional[int] = None


class MealPlanItemResponse(MealPlanItemBase):
    """Schema for meal plan item response"""
    id: UUID
    meal_plan_id: UUID
    created_at: datetime
    meal: Optional[MealResponse] = None  # nested meal details

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# NUTRITION SUMMARY
# ============================================================================

class NutritionSummary(BaseModel):
    """Computed nutrition totals for a meal plan"""
    total_calories: float = 0
    total_protein_grams: float = 0
    total_carbs_grams: float = 0
    total_fat_grams: float = 0
    total_fiber_grams: float = 0
    target_calories: Optional[int] = None
    remaining_calories: Optional[float] = None