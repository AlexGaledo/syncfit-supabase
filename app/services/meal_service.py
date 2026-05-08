"""Meal plan domain logic. Thin handlers in routers delegate here."""
from datetime import date, timedelta
from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.models.meal_plan import Meals, Meal_Plans, Meal_Plan_Items
from app.models.user import User
from app.schemas.meal_plan import (
    MealCreate,
    MealUpdate,
    MealCategory as MealCategorySchema,
    MealPlanCreate,
    MealPlanUpdate,
    MealPlanTemplateCreate,
    MealPlanTemplateUpdate,
    MealPlanItemCreate,
    MealPlanItemUpdate,
    MealPlanGoalApply,
    MealPlanGoalApplyResponse,
    NutritionSummary,
)


DEFAULT_MACRO_SPLIT = (30, 35, 35)


# ---- Internal helpers ----

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


def _normalize_macro_split(profile) -> tuple[int, int, int]:
    if not profile:
        return DEFAULT_MACRO_SPLIT
    protein = profile.macro_protein_pct or DEFAULT_MACRO_SPLIT[0]
    carbs = profile.macro_carb_pct or DEFAULT_MACRO_SPLIT[1]
    fat = profile.macro_fat_pct or DEFAULT_MACRO_SPLIT[2]
    if protein + carbs + fat != 100:
        return DEFAULT_MACRO_SPLIT
    return protein, carbs, fat


def _macro_targets_from_split(
    target_calories: int, split: tuple[int, int, int]
) -> tuple[float, float, float]:
    protein_g = round((target_calories * split[0] / 100) / 4, 1)
    carbs_g = round((target_calories * split[1] / 100) / 4, 1)
    fat_g = round((target_calories * split[2] / 100) / 9, 1)
    return protein_g, carbs_g, fat_g


def _coalesce_macro_targets(
    target_calories: int, split: tuple[int, int, int], payload
) -> tuple[float, float, float]:
    """Uses custom grams from payload if provided safely, otherwise calculates from split."""
    p_grams = getattr(payload, "target_protein_grams", None)
    c_grams = getattr(payload, "target_carbs_grams", None)
    f_grams = getattr(payload, "target_fat_grams", None)

    if p_grams is not None and c_grams is not None and f_grams is not None:
        return p_grams, c_grams, f_grams
    return _macro_targets_from_split(target_calories, split)


def _validate_calorie_floor(target_calories: Optional[int], gender) -> None:
    if target_calories is None:
        return
    g = gender.value if hasattr(gender, "value") else gender
    if g == "male":
        min_cal = 1500
    elif g == "female":
        min_cal = 1200
    else:
        min_cal = 1300
    if target_calories < min_cal:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Daily target must be at least {min_cal} kcal for safety.",
        )


# ---- Plan / template fetchers used by router Depends ----

def get_plan_for_user_or_404(db: Session, user_id: UUID, plan_id: UUID) -> Meal_Plans:
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


def get_template_for_user_or_404(
    db: Session, user_id: UUID, template_id: UUID
) -> Meal_Plans:
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Template not found"
        )
    return template


# ---- Meals (food library) ----

def list_meals(
    db: Session,
    user_id: UUID,
    skip: int,
    limit: int,
    search: Optional[str],
    category: Optional[MealCategorySchema],
) -> List[Meals]:
    query = _visible_meals_query(db, user_id)
    if search:
        query = query.filter(Meals.name.ilike(f"%{search}%"))
    if category:
        query = query.filter(Meals.category == category.value)
    return query.order_by(Meals.name).offset(skip).limit(limit).all()


def get_meal(db: Session, user_id: UUID, meal_id: UUID) -> Meals:
    return _get_visible_meal_or_404(db, user_id, meal_id)


def create_meal(db: Session, user_id: UUID, payload: MealCreate) -> Meals:
    db_meal = Meals(
        **payload.model_dump(exclude={"created_by", "is_custom"}),
        is_custom=True,
        created_by=user_id,
    )
    db.add(db_meal)
    db.commit()
    db.refresh(db_meal)
    return db_meal


def update_meal(
    db: Session, user_id: UUID, meal_id: UUID, payload: MealUpdate
) -> Meals:
    meal = db.query(Meals).filter(Meals.id == meal_id).first()
    if not meal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Meal not found"
        )
    if not meal.is_custom or meal.created_by != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only edit your own custom meals",
        )

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(meal, field, value)

    db.commit()
    db.refresh(meal)
    return meal


def delete_meal(db: Session, user_id: UUID, meal_id: UUID) -> None:
    meal = db.query(Meals).filter(Meals.id == meal_id).first()
    if not meal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Meal not found"
        )
    if not meal.is_custom or meal.created_by != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own custom meals",
        )

    db.delete(meal)
    db.commit()


# ---- Meal plans (daily) ----

def list_my_plans(
    db: Session, user_id: UUID, skip: int, limit: int
) -> List[Meal_Plans]:
    return (
        db.query(Meal_Plans)
        .filter(Meal_Plans.user_id == user_id, Meal_Plans.is_template.is_(False))
        .order_by(Meal_Plans.date.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_plan_by_date(db: Session, user_id: UUID, plan_date: date) -> Meal_Plans:
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No meal plan found for this date",
        )
    return plan


def copy_previous_day_plan(
    db: Session, current_user: User, target_date: date
) -> Meal_Plans:
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
        target_protein_grams=source_plan.target_protein_grams,
        target_carbs_grams=source_plan.target_carbs_grams,
        target_fat_grams=source_plan.target_fat_grams,
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Copied meal plan not found"
        )
    return copied_plan


def create_plan(
    db: Session, current_user: User, payload: MealPlanCreate
) -> Meal_Plans:
    user_id = current_user.id

    existing = (
        db.query(Meal_Plans)
        .filter(
            Meal_Plans.user_id == user_id,
            Meal_Plans.date == payload.date,
            Meal_Plans.is_template.is_(False),
        )
        .first()
    )
    if existing:
        return existing

    target_calories = payload.target_calories
    if target_calories is None and current_user.profile:
        target_calories = current_user.profile.calorie_goal_daily

    _validate_calorie_floor(target_calories, current_user.gender)

    protein_g = carbs_g = fat_g = None
    if target_calories is not None:
        split = _normalize_macro_split(current_user.profile)
        # Use coalesce to respect custom grams if sent in the payload!
        protein_g, carbs_g, fat_g = _coalesce_macro_targets(target_calories, split, payload)

    db_plan = Meal_Plans(
        user_id=user_id,
        date=payload.date,
        notes=payload.notes,
        target_calories=target_calories,
        target_protein_grams=protein_g,
        target_carbs_grams=carbs_g,
        target_fat_grams=fat_g,
    )

    try:
        db.add(db_plan)
        db.commit()
        db.refresh(db_plan)
        return db_plan
    except IntegrityError as e:
        db.rollback()
        if "violates foreign key constraint" in str(e):
            raise HTTPException(
                status_code=400, detail="The specified User ID does not exist."
            )
        raise HTTPException(status_code=409, detail="Database integrity conflict.")


def update_plan(
    db: Session,
    current_user: User,
    plan: Meal_Plans,
    payload: MealPlanUpdate,
) -> Meal_Plans:
    update_data = payload.model_dump(exclude_unset=True)

    if "target_calories" in update_data:
        _validate_calorie_floor(update_data["target_calories"], current_user.gender)
        if not any(
            k in update_data
            for k in ["target_protein_grams", "target_carbs_grams", "target_fat_grams"]
        ):
            split = _normalize_macro_split(current_user.profile)
            protein_g, carbs_g, fat_g = _macro_targets_from_split(
                update_data["target_calories"], split
            )
            update_data.update(
                {
                    "target_protein_grams": protein_g,
                    "target_carbs_grams": carbs_g,
                    "target_fat_grams": fat_g,
                }
            )

    for field, value in update_data.items():
        setattr(plan, field, value)

    db.commit()
    db.refresh(plan)
    return plan


def delete_plan(db: Session, plan: Meal_Plans) -> None:
    db.delete(plan)
    db.commit()


# ---- Templates ----

def list_templates(db: Session, user_id: UUID) -> List[Meal_Plans]:
    return (
        db.query(Meal_Plans)
        .options(joinedload(Meal_Plans.items).joinedload(Meal_Plan_Items.meal))
        .filter(Meal_Plans.user_id == user_id, Meal_Plans.is_template.is_(True))
        .order_by(Meal_Plans.created_at.desc())
        .all()
    )


def create_template(
    db: Session, current_user: User, payload: MealPlanTemplateCreate
) -> Meal_Plans:
    if not payload.template_name.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Template name is required",
        )

    protein_g = carbs_g = fat_g = None
    if payload.target_calories is not None:
        split = _normalize_macro_split(current_user.profile)
        protein_g, carbs_g, fat_g = _macro_targets_from_split(
            payload.target_calories, split
        )

    db_template = Meal_Plans(
        user_id=current_user.id,
        template_name=payload.template_name,
        notes=payload.notes,
        target_calories=payload.target_calories,
        target_protein_grams=protein_g,
        target_carbs_grams=carbs_g,
        target_fat_grams=fat_g,
        is_template=True,
        date=None,
    )
    db.add(db_template)
    db.commit()
    db.refresh(db_template)
    return db_template


def update_template(
    db: Session,
    current_user: User,
    template: Meal_Plans,
    payload: MealPlanTemplateUpdate,
) -> Meal_Plans:
    update_data = payload.model_dump(exclude_unset=True)

    if "target_calories" in update_data and not any(
        k in update_data
        for k in ["target_protein_grams", "target_carbs_grams", "target_fat_grams"]
    ):
        split = _normalize_macro_split(current_user.profile)
        protein_g, carbs_g, fat_g = _macro_targets_from_split(
            update_data["target_calories"], split
        )
        update_data.update(
            {
                "target_protein_grams": protein_g,
                "target_carbs_grams": carbs_g,
                "target_fat_grams": fat_g,
            }
        )

    for field, value in update_data.items():
        setattr(template, field, value)

    db.commit()
    db.refresh(template)
    return template


def delete_template(db: Session, template: Meal_Plans) -> None:
    db.delete(template)
    db.commit()


# ---- Meal plan items ----

def add_meal_to_plan(
    db: Session, user_id: UUID, plan_id: UUID, payload: MealPlanItemCreate
) -> Meal_Plan_Items:
    result = (
        db.query(Meal_Plans, Meals)
        .outerjoin(Meals, (
            (Meals.id == payload.meal_id) &
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

    _meal_plan, meal = result
    if not meal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meal not found or you do not have permission to access it.",
        )

    db_item = Meal_Plan_Items(
        **payload.model_dump(),
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


def update_plan_item(
    db: Session,
    user_id: UUID,
    plan_id: UUID,
    item_id: UUID,
    payload: MealPlanItemUpdate,
) -> Meal_Plan_Items:
    plan = (
        db.query(Meal_Plans)
        .filter(Meal_Plans.id == plan_id, Meal_Plans.user_id == user_id)
        .first()
    )
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Meal plan not found"
        )

    item = (
        db.query(Meal_Plan_Items)
        .filter(
            Meal_Plan_Items.id == item_id,
            Meal_Plan_Items.meal_plan_id == plan_id,
        )
        .first()
    )
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Meal plan item not found"
        )

    for field, value in payload.model_dump(exclude_unset=True).items():
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


def remove_plan_item(
    db: Session, user_id: UUID, plan_id: UUID, item_id: UUID
) -> None:
    plan = (
        db.query(Meal_Plans)
        .filter(Meal_Plans.id == plan_id, Meal_Plans.user_id == user_id)
        .first()
    )
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Meal plan not found"
        )

    item = (
        db.query(Meal_Plan_Items)
        .filter(
            Meal_Plan_Items.id == item_id,
            Meal_Plan_Items.meal_plan_id == plan_id,
        )
        .first()
    )
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Meal plan item not found"
        )

    db.delete(item)
    db.commit()


# ---- Nutrition ----

def get_nutrition_summary(plan: Meal_Plans) -> NutritionSummary:
    total_calories = 0.0
    total_protein = 0.0
    total_carbs = 0.0
    total_fat = 0.0
    total_fiber = 0.0

    for item in plan.items:
        if not item.meal:
            continue

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


# ---- Goal apply ----

def apply_goal_to_future(
    db: Session, current_user: User, target_date: date, payload: MealPlanGoalApply
) -> MealPlanGoalApplyResponse:
    _validate_calorie_floor(payload.target_calories, getattr(current_user, "gender", "other"))
    split = _normalize_macro_split(getattr(current_user, "profile", None))
    protein_g, carbs_g, fat_g = _coalesce_macro_targets(
        payload.target_calories, split, payload
    )

    # Clamp the target date to ensure we NEVER update the past
    safe_target_date = max(target_date, date.today())

    updated = (
        db.query(Meal_Plans)
        .filter(
            Meal_Plans.user_id == current_user.id,
            Meal_Plans.is_template.is_(False),
            Meal_Plans.date >= safe_target_date,  # Uses clamped date
        )
        .update(
            {
                Meal_Plans.target_calories: payload.target_calories,
                Meal_Plans.target_protein_grams: protein_g,
                Meal_Plans.target_carbs_grams: carbs_g,
                Meal_Plans.target_fat_grams: fat_g,
            },
            synchronize_session=False,
        )
    )
    db.commit()
    return MealPlanGoalApplyResponse(updated=updated)
