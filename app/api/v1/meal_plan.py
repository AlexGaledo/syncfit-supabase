"""
Meal Plan API endpoints
- Meals: CRUD for the food library (browse, search, create custom meals)
- Meal Plans: CRUD for daily meal plans
- Templates: CRUD for reusable meal plan templates
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
from app.dependencies import get_current_db_user
from app.models.user import User
from app.models.meal_plan import Meals, Meal_Plans, Meal_Plan_Items
from app.schemas.meal_plan import (
    MealCreate, MealUpdate, MealResponse,
    MealPlanCreate, MealPlanUpdate, MealPlanResponse, MealPlanDetailResponse,
    MealPlanTemplateCreate, MealPlanTemplateUpdate, MealPlanTemplateResponse,
    MealPlanItemCreate, MealPlanItemUpdate, MealPlanItemResponse,
    NutritionSummary, MealCategory as MealCategorySchema,
)

router = APIRouter(prefix="/meal-plans", tags=["Meal Plans"])


def _visible_meals_query(db: Session, user_id: UUID):
    """System meals are public; custom meals are only visible to their owner."""
    return db.query(Meals).filter(
        or_(Meals.is_custom.is_(False), Meals.created_by == user_id)
    )


def _get_visible_meal_or_404(db: Session, user_id: UUID, meal_id: UUID) -> Meals:
    """Helper to retrieve a single meal, checking for visibility."""
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
    current_user: User = Depends(get_current_db_user),
):
    """
    Browse the meal/food library. Supports search by name and filter by category.
    Returns both system meals and the current user's custom meals.
    """
    user_id = current_user.id
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
    current_user: User = Depends(get_current_db_user),
):
    """Get a specific meal from the food library"""
    user_id = current_user.id
    return _get_visible_meal_or_404(db, user_id, meal_id)


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
    user_id = current_user.id
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
    current_user: User = Depends(get_current_db_user),
):
    """Update a custom meal (only the creator can update)"""
    user_id = current_user.id
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
    current_user: User = Depends(get_current_db_user),
):
    """Delete a custom meal (only the creator can delete)"""
    user_id = current_user.id
    meal = db.query(Meals).filter(Meals.id == meal_id).first()
    if not meal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meal not found")
    if not meal.is_custom or meal.created_by != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only delete your own custom meals")

    db.delete(meal)
    db.commit()
    return None


# ============================================================================
# DEPENDENCIES
# ============================================================================

async def get_meal_plan_for_user(
    plan_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_db_user),
) -> Meal_Plans:
    """
    Get a specific daily meal plan for the current user.
    Excludes templates.
    """
    user_id = current_user.id
    plan = (
        db.query(Meal_Plans)
        .options(joinedload(Meal_Plans.items).joinedload(Meal_Plan_Items.meal))
        .filter(
            Meal_Plans.id == plan_id,
            Meal_Plans.user_id == user_id,
            Meal_Plans.is_template.is_(False),
        )
        .first()
    )
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meal plan not found or you do not have permission to access it.",
        )
    return plan


async def get_template_for_user(
    template_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_db_user),
) -> Meal_Plans:
    """
    Get a specific template for the current user.
    """
    user_id = current_user.id
    template = (
        db.query(Meal_Plans)
        .options(joinedload(Meal_Plans.items).joinedload(Meal_Plan_Items.meal))
        .filter(
            Meal_Plans.id == template_id,
            Meal_Plans.user_id == user_id,
            Meal_Plans.is_template.is_(True),
        )
        .first()
    )
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    return template


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
    user_id = current_user.id
    plans = (
        db.query(Meal_Plans)
        .filter(Meal_Plans.user_id == user_id, Meal_Plans.is_template.is_(False))
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
    current_user: User = Depends(get_current_db_user),
):
    """
    Get the daily meal plan for a specific date (with all items and meal details).
    """
    user_id = current_user.id
    plan = (
        db.query(Meal_Plans)
        .options(joinedload(Meal_Plans.items).joinedload(Meal_Plan_Items.meal))
        .filter(
            Meal_Plans.user_id == user_id,
            Meal_Plans.date == plan_date,
            Meal_Plans.is_template.is_(False),
        )
        .first()
    )
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No meal plan found for this date")
    return plan


@router.post("/date/{target_date}/copy-previous", response_model=MealPlanDetailResponse, status_code=status.HTTP_201_CREATED)
async def copy_previous_day_plan(
    target_date: date,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_db_user),
):
    """
    Create a meal plan for `target_date` by copying the previous day's plan.
    """
    user_id = current_user.id
    source_date = target_date - timedelta(days=1)

    existing_target_plan = (
        db.query(Meal_Plans)
        .filter(
            Meal_Plans.user_id == user_id,
            Meal_Plans.date == target_date,
            Meal_Plans.is_template.is_(False),
        )
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
        .filter(
            Meal_Plans.user_id == user_id,
            Meal_Plans.date == source_date,
            Meal_Plans.is_template.is_(False),
        )
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


# ============================================================================
# TEMPLATE ENDPOINTS
# ============================================================================

@router.get("/templates", response_model=List[MealPlanTemplateResponse])
async def list_templates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_db_user),
):
    user_id = current_user.id
    templates = (
        db.query(Meal_Plans)
        .options(joinedload(Meal_Plans.items).joinedload(Meal_Plan_Items.meal))
        .filter(Meal_Plans.user_id == user_id, Meal_Plans.is_template.is_(True))
        .order_by(Meal_Plans.created_at.desc())
        .all()
    )
    return templates


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
    user_id = current_user.id
    if not template_data.template_name.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Template name is required")

    db_template = Meal_Plans(
        user_id=user_id,
        template_name=template_data.template_name,
        notes=template_data.notes,
        target_calories=template_data.target_calories,
        is_template=True,
        date=None,
    )
    db.add(db_template)
    db.commit()
    db.refresh(db_template)
    return db_template


@router.patch("/templates/{template_id}", response_model=MealPlanTemplateResponse)
async def update_template(
    template_data: MealPlanTemplateUpdate,
    template: Meal_Plans = Depends(get_template_for_user),
    db: Session = Depends(get_db),
):
    update_data = template_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(template, field, value)

    db.commit()
    db.refresh(template)
    return template


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template: Meal_Plans = Depends(get_template_for_user),
    db: Session = Depends(get_db),
):
    db.delete(template)
    db.commit()
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
    """
    user_id = current_user.id

    existing = db.query(Meal_Plans).filter(
        Meal_Plans.user_id == user_id,
        Meal_Plans.date == plan_data.date,
        Meal_Plans.is_template.is_(False),
    ).first()

    if existing:
        return existing

    db_plan = Meal_Plans(**plan_data.model_dump(exclude={"template_name"}), user_id=user_id)

    try:
        db.add(db_plan)
        db.commit()
        db.refresh(db_plan)
        return db_plan
    except IntegrityError as e:
        db.rollback()
        if "violates foreign key constraint" in str(e):
            raise HTTPException(status_code=400, detail="The specified User ID does not exist.")
        raise HTTPException(status_code=409, detail="Database integrity conflict.")


@router.patch("/{plan_id}", response_model=MealPlanResponse)
async def update_meal_plan(
    plan_data: MealPlanUpdate,
    plan: Meal_Plans = Depends(get_meal_plan_for_user),
    db: Session = Depends(get_db),
):
    """Update a meal plan's notes or target calories"""
    update_data = plan_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(plan, field, value)

    db.commit()
    db.refresh(plan)
    return plan


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_meal_plan(
    plan: Meal_Plans = Depends(get_meal_plan_for_user),
    db: Session = Depends(get_db),
):
    """Delete a meal plan and all its items"""
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
    current_user: User = Depends(get_current_db_user),
):
    """
    Add a meal from the library to a daily plan.
    Pick a meal, choose the slot (breakfast/lunch/dinner/snack), and set servings.
    """
    user_id = current_user.id

    result = (
        db.query(Meal_Plans, Meals)
        .outerjoin(Meals, (
            (Meals.id == item_data.meal_id) &
            (or_(Meals.is_custom.is_(False), Meals.created_by == user_id))
        ))
        .filter(Meal_Plans.id == plan_id, Meal_Plans.user_id == user_id)
        .first()
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meal plan not found or you do not have permission to access it.",
        )

    meal_plan, meal = result
    if not meal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meal not found or you do not have permission to access it.",
        )

    db_item = Meal_Plan_Items(
        **item_data.model_dump(),
        meal_plan_id=plan_id,
    )

    try:
        db.add(db_item)
        db.commit()
        db.refresh(db_item)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Failed to add meal. It might already be in the plan.",
        ) from exc

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
    current_user: User = Depends(get_current_db_user),
):
    """Update a meal plan item (change servings, meal slot, or order)"""
    user_id = current_user.id

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
    current_user: User = Depends(get_current_db_user),
):
    """Remove a meal from a daily plan"""
    user_id = current_user.id

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
    plan: Meal_Plans = Depends(get_meal_plan_for_user),
):
    """
    Get the nutrition summary for a meal plan.
    Calculates total calories, protein, carbs, fat, and fiber based on
    all items and their serving sizes.
    """
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