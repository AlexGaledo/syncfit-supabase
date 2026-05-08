"""
Meal Plan API endpoints (thin handlers — logic lives in app/services/meal_service).
- Meals: CRUD for the food library (browse, search, create custom meals)
- Meal Plans: CRUD for daily meal plans
- Templates: CRUD for reusable meal plan templates
- Meal Plan Items: Add/remove/update meals in a daily plan
- Nutrition: Summary of daily intake
"""
from datetime import date
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_db_user
from app.models.user import User
from app.models.meal_plan import Meal_Plans
from app.schemas.meal_plan import (
    MealCreate, MealUpdate, MealResponse,
    MealPlanCreate, MealPlanUpdate, MealPlanResponse, MealPlanDetailResponse,
    MealPlanTemplateCreate, MealPlanTemplateUpdate, MealPlanTemplateResponse,
    MealPlanItemCreate, MealPlanItemUpdate, MealPlanItemResponse,
    NutritionSummary, MealCategory as MealCategorySchema,
    MealPlanGoalApply, MealPlanGoalApplyResponse,
)
from app.services import meal_service

router = APIRouter(prefix="/meal-plans", tags=["Meal Plans"])


# ============================================================================
# DEPENDENCIES
# ============================================================================

async def get_meal_plan_for_user(
    plan_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_db_user),
) -> Meal_Plans:
    """Get a specific daily meal plan for the current user. Excludes templates."""
    return meal_service.get_plan_for_user_or_404(db, current_user.id, plan_id)


async def get_template_for_user(
    template_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_db_user),
) -> Meal_Plans:
    """Get a specific template for the current user."""
    return meal_service.get_template_for_user_or_404(db, current_user.id, template_id)


# ============================================================================
# MEALS (FOOD LIBRARY) ENDPOINTS
# ============================================================================

@router.get("/meals", response_model=List[MealResponse])
async def get_meals(
    skip: int = 0,
    limit: int = 50,
    search: Optional[str] = None,
    category: Optional[MealCategorySchema] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_db_user),
):
    """
    Browse the meal/food library. Supports search by name and filter by category.
    Returns both system meals and the current user's custom meals.
    """
    return meal_service.list_meals(db, current_user.id, skip, limit, search, category)


@router.get("/meals/{meal_id}", response_model=MealResponse)
async def get_meal(
    meal_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_db_user),
):
    """Get a specific meal from the food library"""
    return meal_service.get_meal(db, current_user.id, meal_id)


@router.post("/meals", response_model=MealResponse, status_code=status.HTTP_201_CREATED)
async def create_meal(
    meal_data: MealCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_db_user),
):
    """
    Create a custom meal/food in the library.
    Automatically marks it as custom and owned by the current user.
    """
    return meal_service.create_meal(db, current_user.id, meal_data)


@router.patch("/meals/{meal_id}", response_model=MealResponse)
async def update_meal(
    meal_id: UUID,
    meal_data: MealUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_db_user),
):
    """Update a custom meal (only the creator can update)"""
    return meal_service.update_meal(db, current_user.id, meal_id, meal_data)


@router.delete("/meals/{meal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_meal(
    meal_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_db_user),
):
    """Delete a custom meal (only the creator can delete)"""
    meal_service.delete_meal(db, current_user.id, meal_id)
    return None


# ============================================================================
# MEAL PLANS (DAILY PLAN) ENDPOINTS
# ============================================================================

@router.get("/", response_model=List[MealPlanResponse])
async def get_my_meal_plans(
    skip: int = 0,
    limit: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_db_user),
):
    """Get all daily meal plans for the current user, ordered by date descending"""
    return meal_service.list_my_plans(db, current_user.id, skip, limit)


@router.get("/date/{plan_date}", response_model=MealPlanDetailResponse)
async def get_meal_plan_by_date(
    plan_date: date,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_db_user),
):
    """Get the daily meal plan for a specific date (with all items and meal details)."""
    return meal_service.get_plan_by_date(db, current_user.id, plan_date)


@router.post("/date/{target_date}/copy-previous", response_model=MealPlanDetailResponse, status_code=status.HTTP_201_CREATED)
async def copy_previous_day_plan(
    target_date: date,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_db_user),
):
    """Create a meal plan for `target_date` by copying the previous day's plan."""
    return meal_service.copy_previous_day_plan(db, current_user, target_date)


# ============================================================================
# TEMPLATE ENDPOINTS
# ============================================================================

@router.get("/templates", response_model=List[MealPlanTemplateResponse])
async def list_templates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_db_user),
):
    return meal_service.list_templates(db, current_user.id)


@router.get("/templates/{template_id}", response_model=MealPlanTemplateResponse)
async def get_template(
    template: Meal_Plans = Depends(get_template_for_user),
):
    return template


@router.post("/templates", response_model=MealPlanTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    template_data: MealPlanTemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_db_user),
):
    return meal_service.create_template(db, current_user, template_data)


@router.patch("/templates/{template_id}", response_model=MealPlanTemplateResponse)
async def update_template(
    template_data: MealPlanTemplateUpdate,
    template: Meal_Plans = Depends(get_template_for_user),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_db_user),
):
    return meal_service.update_template(db, current_user, template, template_data)


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template: Meal_Plans = Depends(get_template_for_user),
    db: Session = Depends(get_db),
):
    meal_service.delete_template(db, template)
    return None


@router.get("/{plan_id}", response_model=MealPlanDetailResponse)
async def get_meal_plan(
    plan: Meal_Plans = Depends(get_meal_plan_for_user),
):
    """Get a specific daily meal plan by ID with all items"""
    return plan


@router.post("/", response_model=MealPlanResponse, status_code=status.HTTP_201_CREATED)
async def create_meal_plan(
    plan_data: MealPlanCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_db_user),
):
    """
    Create a daily meal plan (get-or-create per date).
    Automatically snapshots target calories and macros based on user profile.
    """
    return meal_service.create_plan(db, current_user, plan_data)


@router.patch("/{plan_id}", response_model=MealPlanResponse)
async def update_meal_plan(
    plan_data: MealPlanUpdate,
    plan: Meal_Plans = Depends(get_meal_plan_for_user),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_db_user),
):
    return meal_service.update_plan(db, current_user, plan, plan_data)


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_meal_plan(
    plan: Meal_Plans = Depends(get_meal_plan_for_user),
    db: Session = Depends(get_db),
):
    """Delete a meal plan and all its items"""
    meal_service.delete_plan(db, plan)
    return None


# ============================================================================
# MEAL PLAN ITEMS (ADD/REMOVE MEALS FROM A PLAN) ENDPOINTS
# ============================================================================

@router.post("/{plan_id}/items", response_model=MealPlanItemResponse, status_code=status.HTTP_201_CREATED)
async def add_meal_to_plan(
    plan_id: UUID,
    item_data: MealPlanItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_db_user),
):
    """
    Add a meal from the library to a daily plan.
    Pick a meal, choose the slot (breakfast/lunch/dinner/snack), and set servings.
    """
    return meal_service.add_meal_to_plan(db, current_user.id, plan_id, item_data)


@router.patch("/{plan_id}/items/{item_id}", response_model=MealPlanItemResponse)
async def update_meal_plan_item(
    plan_id: UUID,
    item_id: UUID,
    item_data: MealPlanItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_db_user),
):
    """Update a meal plan item (change servings, meal slot, or order)"""
    return meal_service.update_plan_item(db, current_user.id, plan_id, item_id, item_data)


@router.delete("/{plan_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_meal_from_plan(
    plan_id: UUID,
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_db_user),
):
    """Remove a meal from a daily plan"""
    meal_service.remove_plan_item(db, current_user.id, plan_id, item_id)
    return None


# ============================================================================
# NUTRITION SUMMARY ENDPOINT
# ============================================================================

@router.get("/{plan_id}/nutrition", response_model=NutritionSummary)
async def get_nutrition_summary(
    plan: Meal_Plans = Depends(get_meal_plan_for_user),
):
    """
    Get the nutrition summary for a meal plan.
    Calculates total calories, protein, carbs, fat, and fiber based on
    all items and their serving sizes.
    """
    return meal_service.get_nutrition_summary(plan)


@router.post("/date/{target_date}/apply-goal", response_model=MealPlanGoalApplyResponse)
async def apply_goal_to_future(
    target_date: date,
    payload: MealPlanGoalApply,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_db_user),
):
    return meal_service.apply_goal_to_future(db, current_user, target_date, payload)
