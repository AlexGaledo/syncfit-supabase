"""
Meal Plan API endpoints
- Meals: CRUD for the food library (browse, search, create custom meals)
- Meal Plans: CRUD for daily meal plans
- Meal Plan Items: Add/remove/update meals in a daily plan
- Nutrition: Summary of daily intake
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from uuid import UUID
from datetime import date, timedelta

from app.database import get_db
from app.dependencies import get_current_user
from app.models.meal_plan import Meals, Meal_Plans, Meal_Plan_Items
from app.schemas.meal_plan import (
    MealCreate, MealUpdate, MealResponse,
    MealPlanCreate, MealPlanUpdate, MealPlanResponse, MealPlanDetailResponse,
    MealPlanItemCreate, MealPlanItemUpdate, MealPlanItemResponse,
    NutritionSummary, MealCategory as MealCategorySchema,
)

router = APIRouter(prefix="/meal-plans", tags=["Meal Plans"])


def _parse_current_user_id(current_user: dict) -> UUID:
    """Extract and validate the authenticated user id from JWT claims."""
    raw_user_id = current_user.get("sub")
    if not raw_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authenticated user identifier",
        )
    try:
        return UUID(str(raw_user_id))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authenticated user identifier",
        ) from exc


def _visible_meals_query(db: Session, user_id: UUID):
    """System meals are public; custom meals are only visible to their owner."""
    return db.query(Meals).filter(
        or_(Meals.is_custom.is_(False), Meals.created_by == user_id)
    )


def _get_visible_meal_or_404(db: Session, user_id: UUID, meal_id: UUID) -> Meals:
    meal = _visible_meals_query(db, user_id).filter(Meals.id == meal_id).first()
    if not meal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meal not found",
        )
    return meal


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
    current_user: dict = Depends(get_current_user),
):
    """
    Browse the meal/food library. Supports search by name and filter by category.
    Returns both system meals and the current user's custom meals.
    """
    user_id = _parse_current_user_id(current_user)
    query = _visible_meals_query(db, user_id)

    if search:
        query = query.filter(Meals.name.ilike(f"%{search}%"))
    if category:
        query = query.filter(Meals.category == category.value)

    meals = query.order_by(Meals.name).offset(skip).limit(limit).all()
    return meals


@router.get("/meals/{meal_id}", response_model=MealResponse)
async def get_meal(
    meal_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get a specific meal from the food library"""
    user_id = _parse_current_user_id(current_user)
    return _get_visible_meal_or_404(db, user_id, meal_id)


@router.post("/meals", response_model=MealResponse, status_code=status.HTTP_201_CREATED)
async def create_meal(
    meal_data: MealCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Create a custom meal/food in the library.
    Automatically marks it as custom and owned by the current user.
    """
    user_id = _parse_current_user_id(current_user)
    db_meal = Meals(
        **meal_data.model_dump(exclude={"created_by", "is_custom"}),
        is_custom=True,
        created_by=user_id,
    )
    db.add(db_meal)
    db.commit()
    db.refresh(db_meal)
    return db_meal


@router.patch("/meals/{meal_id}", response_model=MealResponse)
async def update_meal(
    meal_id: UUID,
    meal_data: MealUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Update a custom meal (only the creator can update)"""
    user_id = _parse_current_user_id(current_user)
    meal = db.query(Meals).filter(Meals.id == meal_id).first()
    if not meal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meal not found")
    if not meal.is_custom or meal.created_by != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only edit your own custom meals")

    update_data = meal_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(meal, field, value)

    db.commit()
    db.refresh(meal)
    return meal


@router.delete("/meals/{meal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_meal(
    meal_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Delete a custom meal (only the creator can delete)"""
    user_id = _parse_current_user_id(current_user)
    meal = db.query(Meals).filter(Meals.id == meal_id).first()
    if not meal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meal not found")
    if not meal.is_custom or meal.created_by != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only delete your own custom meals")

    db.delete(meal)
    db.commit()
    return None


# ============================================================================
# MEAL PLANS (DAILY PLAN) ENDPOINTS
# ============================================================================

@router.get("/", response_model=List[MealPlanResponse])
async def get_my_meal_plans(
    skip: int = 0,
    limit: int = 30,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get all meal plans for the current user, ordered by date descending"""
    user_id = _parse_current_user_id(current_user)
    plans = (
        db.query(Meal_Plans)
        .filter(Meal_Plans.user_id == user_id)
        .order_by(Meal_Plans.date.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return plans


@router.get("/date/{plan_date}", response_model=MealPlanDetailResponse)
async def get_meal_plan_by_date(
    plan_date: date,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Get the meal plan for a specific date (with all items and meal details).
    This is the main view a user sees when opening a day in the app.
    """
    user_id = _parse_current_user_id(current_user)
    plan = (
        db.query(Meal_Plans)
        .options(joinedload(Meal_Plans.items).joinedload(Meal_Plan_Items.meal))
        .filter(Meal_Plans.user_id == user_id, Meal_Plans.date == plan_date)
        .first()
    )
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No meal plan found for this date")
    return plan


@router.post("/date/{target_date}/copy-previous", response_model=MealPlanDetailResponse, status_code=status.HTTP_201_CREATED)
async def copy_previous_day_plan(
    target_date: date,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Create a meal plan for `target_date` by copying the previous day's plan.
    This mirrors a common quick-log workflow from nutrition trackers.
    """
    user_id = _parse_current_user_id(current_user)
    source_date = target_date - timedelta(days=1)

    existing_target_plan = (
        db.query(Meal_Plans)
        .filter(Meal_Plans.user_id == user_id, Meal_Plans.date == target_date)
        .first()
    )
    if existing_target_plan:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A meal plan already exists for the target date.",
        )

    source_plan = (
        db.query(Meal_Plans)
        .options(joinedload(Meal_Plans.items))
        .filter(Meal_Plans.user_id == user_id, Meal_Plans.date == source_date)
        .first()
    )
    if not source_plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No previous-day meal plan found to copy.",
        )

    copied_plan = Meal_Plans(
        user_id=user_id,
        date=target_date,
        notes=source_plan.notes,
        target_calories=source_plan.target_calories,
    )
    try:
        db.add(copied_plan)
        db.flush()

        copied_items = [
            Meal_Plan_Items(
                meal_plan_id=copied_plan.id,
                meal_id=item.meal_id,
                meal_type=item.meal_type,
                servings=item.servings,
                order_index=item.order_index,
            )
            for item in source_plan.items
        ]
        if copied_items:
            db.add_all(copied_items)

        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A meal plan already exists for the target date.",
        )

    copied_plan = (
        db.query(Meal_Plans)
        .options(joinedload(Meal_Plans.items).joinedload(Meal_Plan_Items.meal))
        .filter(Meal_Plans.id == copied_plan.id, Meal_Plans.user_id == user_id)
        .first()
    )
    if not copied_plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Copied meal plan not found")
    return copied_plan


@router.get("/{plan_id}", response_model=MealPlanDetailResponse)
async def get_meal_plan(
    plan_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get a specific meal plan by ID with all items"""
    user_id = _parse_current_user_id(current_user)
    plan = (
        db.query(Meal_Plans)
        .options(joinedload(Meal_Plans.items).joinedload(Meal_Plan_Items.meal))
        .filter(Meal_Plans.id == plan_id, Meal_Plans.user_id == user_id)
        .first()
    )
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meal plan not found")
    return plan


@router.post("/", response_model=MealPlanResponse, status_code=status.HTTP_201_CREATED)
async def create_meal_plan(
    plan_data: MealPlanCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Create a new daily meal plan. Only one plan per user per date.
    """
    user_id = _parse_current_user_id(current_user)

    # Check if a plan already exists for this date
    existing = (
        db.query(Meal_Plans)
        .filter(Meal_Plans.user_id == user_id, Meal_Plans.date == plan_data.date)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A meal plan already exists for this date. Use the existing plan or update it.",
        )

    db_plan = Meal_Plans(**plan_data.model_dump(exclude={"template_name"}), user_id=user_id)
    db.add(db_plan)

    # If a template was provided, apply it
    if plan_data.template_name:
        # In a real implementation, you would fetch the template's meals
        # from the database here and create Meal_Plan_Items for them.
        # For now, we can just add a note.
        db_plan.notes = f"Started with template: {plan_data.template_name}"

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A meal plan already exists for this date.",
        )
    db.refresh(db_plan)
    return db_plan


@router.patch("/{plan_id}", response_model=MealPlanResponse)
async def update_meal_plan(
    plan_id: UUID,
    plan_data: MealPlanUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Update a meal plan's notes or target calories"""
    user_id = _parse_current_user_id(current_user)
    plan = db.query(Meal_Plans).filter(Meal_Plans.id == plan_id, Meal_Plans.user_id == user_id).first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meal plan not found")

    update_data = plan_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(plan, field, value)

    db.commit()
    db.refresh(plan)
    return plan


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_meal_plan(
    plan_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Delete a meal plan and all its items"""
    user_id = _parse_current_user_id(current_user)
    plan = db.query(Meal_Plans).filter(Meal_Plans.id == plan_id, Meal_Plans.user_id == user_id).first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meal plan not found")

    db.delete(plan)
    db.commit()
    return None


# ============================================================================
# MEAL PLAN ITEMS (ADD/REMOVE MEALS FROM A PLAN) ENDPOINTS
# ============================================================================

@router.post("/{plan_id}/items", response_model=MealPlanItemResponse, status_code=status.HTTP_201_CREATED)
async def add_meal_to_plan(
    plan_id: UUID,
    item_data: MealPlanItemCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Add a meal from the library to a daily plan.
    Pick a meal, choose the slot (breakfast/lunch/dinner/snack), and set servings.
    """
    user_id = _parse_current_user_id(current_user)

    # Verify plan belongs to user
    plan = db.query(Meal_Plans).filter(Meal_Plans.id == plan_id, Meal_Plans.user_id == user_id).first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meal plan not found")

    # Verify meal exists and is visible to the current user
    _get_visible_meal_or_404(db, user_id, item_data.meal_id)

    db_item = Meal_Plan_Items(**item_data.model_dump(), meal_plan_id=plan_id)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)

    # Eager-load the meal relationship for the response
    db_item = (
        db.query(Meal_Plan_Items)
        .options(joinedload(Meal_Plan_Items.meal))
        .filter(Meal_Plan_Items.id == db_item.id)
        .first()
    )
    return db_item


@router.patch("/{plan_id}/items/{item_id}", response_model=MealPlanItemResponse)
async def update_meal_plan_item(
    plan_id: UUID,
    item_id: UUID,
    item_data: MealPlanItemUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Update a meal plan item (change servings, meal slot, or order)"""
    user_id = _parse_current_user_id(current_user)

    # Verify plan belongs to user
    plan = db.query(Meal_Plans).filter(Meal_Plans.id == plan_id, Meal_Plans.user_id == user_id).first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meal plan not found")

    item = db.query(Meal_Plan_Items).filter(
        Meal_Plan_Items.id == item_id, Meal_Plan_Items.meal_plan_id == plan_id
    ).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meal plan item not found")

    update_data = item_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)

    db.commit()
    db.refresh(item)

    # Eager-load meal for response
    item = (
        db.query(Meal_Plan_Items)
        .options(joinedload(Meal_Plan_Items.meal))
        .filter(Meal_Plan_Items.id == item.id)
        .first()
    )
    return item


@router.delete("/{plan_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_meal_from_plan(
    plan_id: UUID,
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Remove a meal from a daily plan"""
    user_id = _parse_current_user_id(current_user)

    # Verify plan belongs to user
    plan = db.query(Meal_Plans).filter(Meal_Plans.id == plan_id, Meal_Plans.user_id == user_id).first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meal plan not found")

    item = db.query(Meal_Plan_Items).filter(
        Meal_Plan_Items.id == item_id, Meal_Plan_Items.meal_plan_id == plan_id
    ).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meal plan item not found")

    db.delete(item)
    db.commit()
    return None


# ============================================================================
# NUTRITION SUMMARY ENDPOINT
# ============================================================================

@router.get("/{plan_id}/nutrition", response_model=NutritionSummary)
async def get_nutrition_summary(
    plan_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Get the nutrition summary for a meal plan.
    Calculates total calories, protein, carbs, fat, and fiber based on
    all items and their serving sizes.
    """
    user_id = _parse_current_user_id(current_user)
    plan = (
        db.query(Meal_Plans)
        .options(joinedload(Meal_Plans.items).joinedload(Meal_Plan_Items.meal))
        .filter(Meal_Plans.id == plan_id, Meal_Plans.user_id == user_id)
        .first()
    )
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meal plan not found")

    total_calories = 0.0
    total_protein = 0.0
    total_carbs = 0.0
    total_fat = 0.0
    total_fiber = 0.0

    for item in plan.items:
        meal = item.meal
        servings = item.servings or 1.0
        total_calories += (meal.calories or 0) * servings
        total_protein += (meal.protein_grams or 0) * servings
        total_carbs += (meal.carbs_grams or 0) * servings
        total_fat += (meal.fat_grams or 0) * servings
        total_fiber += (meal.fiber_grams or 0) * servings

    remaining = None
    if plan.target_calories is not None:
        remaining = plan.target_calories - total_calories

    return NutritionSummary(
        total_calories=round(total_calories, 1),
        total_protein_grams=round(total_protein, 1),
        total_carbs_grams=round(total_carbs, 1),
        total_fat_grams=round(total_fat, 1),
        total_fiber_grams=round(total_fiber, 1),
        target_calories=plan.target_calories,
        remaining_calories=round(remaining, 1) if remaining is not None else None,
    )