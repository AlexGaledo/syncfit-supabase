"""Workout API endpoints - Ford"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.dependencies import get_current_db_user
from app.models.item import (
    Exercises, Workouts, Workout_Plans, Exercises_Workouts, Workouts_Workout_Plans,
    Plan_Tags, Workout_Plans_Plan_Tags, Exer_Tags, Exercises_Exer_Tags
)
from app.schemas.item import (
    ExerciseCreate, ExerciseUpdate, ExerciseResponse,
    WorkoutCreate, WorkoutUpdate, WorkoutResponse,
    WorkoutPlanCreate, WorkoutPlanUpdate, WorkoutPlanResponse,
    ExercisesWorkoutsCreate, ExercisesWorkoutsResponse,
    WorkoutsWorkoutPlansCreate, WorkoutsWorkoutPlansResponse,
    SeederFullWorkoutPlan,
    FullWorkoutPlanDetailResponse, FullWorkoutDetail, FullExerciseDetail,
    ExerTagCreate, ExerTagResponse,
    PlanTagCreate, PlanTagResponse,
    ExercisesExerTagsCreate, ExercisesExerTagsResponse,
    WorkoutPlansPlanTagsCreate, WorkoutPlansPlanTagsResponse,
)

workout_router = APIRouter(prefix="/workout", tags=["Workout"])


@workout_router.post("/exercises", response_model=List[ExerciseResponse], status_code=status.HTTP_201_CREATED)
def create_exercises(
    exercises: List[ExerciseCreate],
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Create one or more new exercises. If an exercise with the same name already exists, reuse it instead of creating a duplicate.
    """
    created_exercises = []
    for exercise_data in exercises:
        ex_dump = exercise_data.model_dump()
        ex_tags = ex_dump.pop("tags", []) or []

        # Check if the exercise already exists by name
        existing_exercise = db.query(Exercises).filter(Exercises.name == exercise_data.name).first()
        if existing_exercise:
            db_exercise = existing_exercise
        else:
            # Create a new exercise if it doesn't exist
            db_exercise = Exercises(**ex_dump)
            db.add(db_exercise)
            db.flush()
        
        # Process tags
        for tag_name in ex_tags:
            db_tag = db.query(Exer_Tags).filter(Exer_Tags.name == tag_name).first()
            if not db_tag:
                db_tag = Exer_Tags(name=tag_name)
                db.add(db_tag)
                db.flush()
            
            link_exists = db.query(Exercises_Exer_Tags).filter_by(exercise_id=db_exercise.id, tag_id=db_tag.id).first()
            if not link_exists:
                db.add(Exercises_Exer_Tags(exercise_id=db_exercise.id, tag_id=db_tag.id))
                db.flush()
                
        created_exercises.append(db_exercise)
    
    db.commit()
    for exercise in created_exercises:
        db.refresh(exercise)
        
    return created_exercises


@workout_router.get("/exercises", response_model=List[ExerciseResponse])
def get_all_exercises(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Retrieve all exercises.
    """
    exercises = db.query(Exercises).offset(skip).limit(limit).all()
    
    result = []
    for ex in exercises:
        ex_dict = {
            "id": ex.id,
            "name": ex.name,
            "description": ex.description,
            "instruction": ex.instruction,
            "is_equipment_needed": ex.is_equipment_needed,
            "video_url": ex.video_url,
            "image_url": ex.image_url,
            "created_at": ex.created_at,
            "tags": [link.tag.name for link in ex.exercise_exer_tags] if ex.exercise_exer_tags else []
        }
        result.append(ex_dict)
        
    return result


@workout_router.post("/workouts", response_model=WorkoutResponse, status_code=status.HTTP_201_CREATED)
def create_workout(
    workout: WorkoutCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new workout session.
    """
    db_workout = Workouts(**workout.model_dump())
    db.add(db_workout)
    db.commit()
    db.refresh(db_workout)
    return db_workout


@workout_router.post("/workout-plans", response_model=WorkoutPlanResponse, status_code=status.HTTP_201_CREATED)
def create_workout_plan(
    workout_plan: WorkoutPlanCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new workout plan.
    """
    db_workout_plan = Workout_Plans(**workout_plan.model_dump())
    db.add(db_workout_plan)
    db.commit()
    db.refresh(db_workout_plan)
    return db_workout_plan


@workout_router.post("/exercises-workouts", response_model=ExercisesWorkoutsResponse, status_code=status.HTTP_201_CREATED)
def create_exercise_workout_link(
    link: ExercisesWorkoutsCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Link an exercise to a workout.
    """
    db_link = Exercises_Workouts(**link.model_dump())
    db.add(db_link)
    db.commit()
    db.refresh(db_link)
    return db_link


@workout_router.post("/workouts-workout-plans", response_model=WorkoutsWorkoutPlansResponse, status_code=status.HTTP_201_CREATED)
def create_workout_workout_plan_link(
    link: WorkoutsWorkoutPlansCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Link a workout to a workout plan.
    """
    db_link = Workouts_Workout_Plans(**link.model_dump())
    db.add(db_link)
    db.commit()
    db.refresh(db_link)
    return db_link


@workout_router.post("/seed-full-workout-plan", status_code=status.HTTP_201_CREATED)
def seed_full_workout_plan(
    plan_data: SeederFullWorkoutPlan,
    db: Session = Depends(get_db),
    current_db_user: User = Depends(get_current_db_user)
):
    """
    Seeds a complete workout plan, including exercises, workouts, and their associations.
    This is a generic seeder that accepts a JSON payload with the full plan structure.
    All operations are performed in a single transaction.
    """
    try:
        # 1. Create all exercises
        created_exercises = {}
        for exercise_data in plan_data.exercises:
            ex_dump = exercise_data.model_dump()
            ex_tags = ex_dump.pop("tags", []) or []
            
            db_exercise = db.query(Exercises).filter(Exercises.name == exercise_data.name).first()
            if not db_exercise:
                db_exercise = Exercises(**ex_dump)
                db.add(db_exercise)
                db.flush()
                
            # Process exercise tags
            for tag_name in ex_tags:
                db_tag = db.query(Exer_Tags).filter(Exer_Tags.name == tag_name).first()
                if not db_tag:
                    db_tag = Exer_Tags(name=tag_name)
                    db.add(db_tag)
                    db.flush()
                
                # Link tag to exercise
                link_exists = db.query(Exercises_Exer_Tags).filter_by(exercise_id=db_exercise.id, tag_id=db_tag.id).first()
                if not link_exists:
                    db_ex_tag_link = Exercises_Exer_Tags(exercise_id=db_exercise.id, tag_id=db_tag.id)
                    db.add(db_ex_tag_link)

            created_exercises[exercise_data.name] = db_exercise

        # Flush to assign IDs to new exercises so they can be referenced
        db.flush()

        # 2. Create the workout plan
        plan_info = plan_data.plan
        db_plan = db.query(Workout_Plans).filter(Workout_Plans.title == plan_info.title).first()
        if not db_plan:
            db_plan = Workout_Plans(
                title=plan_info.title,
                description=plan_info.description,
                duration_minutes=plan_info.duration_minutes,
                difficulty=plan_info.difficulty,
                days_per_week=plan_info.days_per_week,
                ai_generated=plan_info.ai_generated,
                is_trainer_provided=plan_info.is_trainer_provided,
                is_preset=plan_info.is_preset,
                is_equipment_needed=plan_info.is_equipment_needed,
                image_url=plan_info.image_url,
                created_by=current_db_user.id,
            )
            db.add(db_plan)
            # Flush to assign ID to the new plan
            db.flush()

        # Process plan tags
        plan_tags = plan_info.tags or []
        for tag_name in plan_tags:
            db_tag = db.query(Plan_Tags).filter(Plan_Tags.name == tag_name).first()
            if not db_tag:
                db_tag = Plan_Tags(name=tag_name)
                db.add(db_tag)
                db.flush()
            
            link_exists = db.query(Workout_Plans_Plan_Tags).filter_by(plan_id=db_plan.id, tag_id=db_tag.id).first()
            if not link_exists:
                db.add(Workout_Plans_Plan_Tags(plan_id=db_plan.id, tag_id=db_tag.id))
                db.flush()

        # 3. Create workouts and link everything together
        for workout_data in plan_info.workouts:
            db_workout = db.query(Workouts).filter(Workouts.title == workout_data.title).first()
            if not db_workout:
                db_workout = Workouts(
                    title=workout_data.title,
                    description=workout_data.description,
                    estimated_duration_minutes=workout_data.estimated_duration_minutes
                )
                db.add(db_workout)
                # Flush to assign ID to the new workout
                db.flush()

            # Link workout to plan for the specified day
            link_exists = db.query(Workouts_Workout_Plans).filter_by(
                plan_id=db_plan.id, 
                workout_id=db_workout.id,
                day_of_week=workout_data.day_of_week
            ).first()
            if not link_exists:
                db_link = Workouts_Workout_Plans(
                    plan_id=db_plan.id,
                    workout_id=db_workout.id,
                    order_index=workout_data.order_index,
                    day_of_week=workout_data.day_of_week
                )
                db.add(db_link)

            # Link exercises to workout
            for ex_workout_data in workout_data.exercises:
                exercise_obj = created_exercises.get(ex_workout_data.exercise_name)
                if not exercise_obj:
                    # This will cause a rollback, which is what we want if data is inconsistent
                    raise HTTPException(status_code=404, detail=f"Exercise '{ex_workout_data.exercise_name}' not found in provided list.")

                link_exists = db.query(Exercises_Workouts).filter_by(workout_id=db_workout.id, exercise_id=exercise_obj.id).first()
                if not link_exists:
                    link_data = {
                        "workout_id": db_workout.id,
                        "exercise_id": exercise_obj.id,
                        "order_index": ex_workout_data.order_index,
                        "sets": ex_workout_data.sets,
                        "reps": ex_workout_data.reps,
                        "is_by_reps": ex_workout_data.is_by_reps,
                        "is_by_duration": ex_workout_data.is_by_duration,
                        "duration_seconds": ex_workout_data.duration_seconds,
                        "rest_duration_seconds": ex_workout_data.rest_duration_seconds,
                    }
                    db_link = Exercises_Workouts(**link_data)
                    db.add(db_link)
        
        db.commit()

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An error occurred: {str(e)}")

    # Refresh objects after commit to get final state from DB
    db.refresh(db_plan)
    # We don't need to refresh all objects unless we return them.
    # The success message is sufficient.
    return {"message": f"Workout plan '{plan_info.title}' seeded successfully."}


@workout_router.get("/workout-plans/{plan_id}/full", response_model=FullWorkoutPlanDetailResponse)
def get_full_workout_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Retrieve all details of a workout plan, including its associated workouts and their exercises.
    """
    plan = db.query(Workout_Plans).filter(Workout_Plans.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Workout plan not found")

    workouts_links = db.query(Workouts_Workout_Plans).filter(Workouts_Workout_Plans.plan_id == plan_id).all()
    
    full_workouts = []
    for link in workouts_links:
        workout_obj = link.workout
        
        exercises_links = db.query(Exercises_Workouts).filter(Exercises_Workouts.workout_id == workout_obj.id).all()
        full_exercises = []
        for ex_link in exercises_links:
            ex_obj = ex_link.exercise
            ex_tags = [link.tag.name for link in ex_obj.exercise_exer_tags] if ex_obj.exercise_exer_tags else []
            full_exercises.append(
                FullExerciseDetail(
                    exercise_id=ex_obj.id,
                    name=ex_obj.name,
                    description=ex_obj.description,
                    instruction=ex_obj.instruction,
                    is_equipment_needed=ex_obj.is_equipment_needed,
                    video_url=ex_obj.video_url,
                    image_url=ex_obj.image_url,
                    tags=ex_tags,
                    sets=ex_link.sets, # type: ignore
                    reps=ex_link.reps, # type: ignore
                    is_by_reps=ex_link.is_by_reps, # type: ignore
                    is_by_duration=ex_link.is_by_duration, # type: ignore
                    duration_seconds=ex_link.duration_seconds, # type: ignore
                    rest_duration_seconds=ex_link.rest_duration_seconds, # type: ignore
                    order_index=ex_link.order_index # type: ignore
                )
            )
            
        full_workouts.append(
            FullWorkoutDetail(
                workout_id=workout_obj.id,
                title=workout_obj.title,
                description=workout_obj.description,
                estimated_duration_minutes=workout_obj.estimated_duration_minutes,
                day_of_week=link.day_of_week, # type: ignore
                order_index=link.order_index, # type: ignore
                exercises=sorted(full_exercises, key=lambda x: x.order_index or 0)
            )
        )

    plan_tags = [link.tag.name for link in plan.workout_plan_tags] if plan.workout_plan_tags else []

    return FullWorkoutPlanDetailResponse(
        plan_id=plan.id, # type: ignore
        title=plan.title, # type: ignore
        description=plan.description, # type: ignore
        duration_minutes=plan.duration_minutes, # type: ignore
        difficulty=plan.difficulty, # type: ignore
        days_per_week=plan.days_per_week, # type: ignore
        ai_generated=plan.ai_generated, # type: ignore
        is_trainer_provided=plan.is_trainer_provided, # type: ignore
        is_preset=plan.is_preset, # type: ignore
        is_equipment_needed=plan.is_equipment_needed, # type: ignore
        image_url=plan.image_url, # type: ignore
        created_by=plan.created_by, # type: ignore
        tags=plan_tags,
        workouts=sorted(full_workouts, key=lambda x: x.order_index)
    )

@workout_router.get("/workout-plans/user/{user_id}", response_model=List[WorkoutPlanResponse])
def get_workout_plans_by_user(
    user_id: UUID,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Retrieve all workout plans created by a specific user.
    """
    plans = db.query(Workout_Plans).filter(Workout_Plans.created_by == user_id).offset(skip).limit(limit).all()
    return plans


@workout_router.get("/exer-tags", response_model=List[ExerTagResponse])
def get_all_exer_tags(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Retrieve all exercise tags.
    """
    tags = db.query(Exer_Tags).offset(skip).limit(limit).all()
    return tags


@workout_router.post("/exer-tags", response_model=List[ExerTagResponse], status_code=status.HTTP_201_CREATED)
def create_exer_tags(
    tags: List[ExerTagCreate],
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Create multiple exercise tags using a list of tag names. See exer_tags.json for example input.
    """
    created_tags = []
    for tag_data in tags:
        existing_tag = db.query(Exer_Tags).filter(Exer_Tags.name == tag_data.name).first()
        if existing_tag:
            created_tags.append(existing_tag)
        else:
            new_tag = Exer_Tags(name=tag_data.name)
            db.add(new_tag)
            db.flush()
            created_tags.append(new_tag)
            
    db.commit()
    for tag in created_tags:
        db.refresh(tag)
        
    return created_tags


@workout_router.get("/plan-tags", response_model=List[PlanTagResponse])
def get_all_plan_tags(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Retrieve all plan tags.
    """
    tags = db.query(Plan_Tags).offset(skip).limit(limit).all()
    return tags


@workout_router.post("/plan-tags", response_model=List[PlanTagResponse], status_code=status.HTTP_201_CREATED)
def create_plan_tags(
    tags: List[PlanTagCreate],
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Create multiple plan tags using a list of tag names. See plan_tags.json for example input.
    """
    created_tags = []
    for tag_data in tags:
        existing_tag = db.query(Plan_Tags).filter(Plan_Tags.name == tag_data.name).first()
        if existing_tag:
            created_tags.append(existing_tag)
        else:
            new_tag = Plan_Tags(name=tag_data.name)
            db.add(new_tag)
            db.flush()
            created_tags.append(new_tag)
            
    db.commit()
    for tag in created_tags:
        db.refresh(tag)
        
    return created_tags


@workout_router.post("/exercises-tags", response_model=ExercisesExerTagsResponse, status_code=status.HTTP_201_CREATED)
def create_exercise_tag_link(
    link: ExercisesExerTagsCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Link a tag to an exercise using tag_id and exercise_id
    """
    ex = db.query(Exercises).filter(Exercises.id == link.exercise_id).first()
    if not ex:
        raise HTTPException(status_code=404, detail="Exercise not found")
    tag = db.query(Exer_Tags).filter(Exer_Tags.id == link.tag_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
        
    link_exists = db.query(Exercises_Exer_Tags).filter_by(exercise_id=link.exercise_id, tag_id=link.tag_id).first()
    if link_exists:
        return link_exists
        
    db_link = Exercises_Exer_Tags(**link.model_dump())
    db.add(db_link)
    db.commit()
    return link


@workout_router.post("/workout-plans-tags", response_model=WorkoutPlansPlanTagsResponse, status_code=status.HTTP_201_CREATED)
def create_workout_plan_tag_link(
    link: WorkoutPlansPlanTagsCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Link a tag to a workout plan using tag_id and plan_id
    """
    plan = db.query(Workout_Plans).filter(Workout_Plans.id == link.plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Workout plan not found")
    tag = db.query(Plan_Tags).filter(Plan_Tags.id == link.tag_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
        
    link_exists = db.query(Workout_Plans_Plan_Tags).filter_by(plan_id=link.plan_id, tag_id=link.tag_id).first()
    if link_exists:
        return link_exists
        
    db_link = Workout_Plans_Plan_Tags(**link.model_dump())
    db.add(db_link)
    db.commit()
    return link


@workout_router.get("/test-current-user")
def test_current_user(current_db_user: User = Depends(get_current_db_user)):
    """
    Returns the current user's database object for debugging.
    """
    return current_db_user


# ============================================================================
# WORKOUT PLANS — LIST / UPDATE / DELETE
# ============================================================================

@workout_router.get("/workout-plans", response_model=List[WorkoutPlanResponse])
def get_workout_plans(
    assigned_to: UUID = None, #type:ignore
    created_by: UUID = None, #type:ignore
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    List workout plans. Optionally filter by assigned_to or created_by.
    """
    query = db.query(Workout_Plans)
    if assigned_to:
        query = query.filter(Workout_Plans.assigned_to == assigned_to)
    if created_by:
        query = query.filter(Workout_Plans.created_by == created_by)
    return query.offset(skip).limit(limit).all()


@workout_router.patch("/workout-plans/{plan_id}", response_model=WorkoutPlanResponse)
def update_workout_plan(
    plan_id: int,
    plan_data: WorkoutPlanUpdate,
    db: Session = Depends(get_db),
    current_db_user: User = Depends(get_current_db_user),
):
    """
    Update a workout plan's metadata. Only the creator or an admin may do this.
    """
    plan = db.query(Workout_Plans).filter(Workout_Plans.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workout plan not found")

    if plan.created_by != current_db_user.id and current_db_user.role.value != "admin": #type:ignore
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only update your own workout plans")

    update_data = plan_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(plan, field, value)

    db.commit()
    db.refresh(plan)
    return plan


@workout_router.delete("/workout-plans/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workout_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    current_db_user: User = Depends(get_current_db_user),
):
    """
    Delete a workout plan. Only the creator or an admin may do this.
    """
    plan = db.query(Workout_Plans).filter(Workout_Plans.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workout plan not found")

    if plan.created_by != current_db_user.id and current_db_user.role.value != "admin": #type:ignore
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only delete your own workout plans")

    db.delete(plan)
    db.commit()
    return None


# ============================================================================
# WORKOUTS — LIST / GET / UPDATE / DELETE
# ============================================================================

@workout_router.get("/workouts", response_model=List[WorkoutResponse])
def get_all_workouts(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Retrieve all workouts."""
    return db.query(Workouts).offset(skip).limit(limit).all()


@workout_router.get("/workouts/{workout_id}", response_model=WorkoutResponse)
def get_workout(
    workout_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Retrieve a single workout by ID."""
    workout = db.query(Workouts).filter(Workouts.id == workout_id).first()
    if not workout:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workout not found")
    return workout


@workout_router.patch("/workouts/{workout_id}", response_model=WorkoutResponse)
def update_workout(
    workout_id: int,
    workout_data: WorkoutUpdate,
    db: Session = Depends(get_db),
    current_db_user: User = Depends(get_current_db_user),
):
    """Update a workout."""
    workout = db.query(Workouts).filter(Workouts.id == workout_id).first()
    if not workout:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workout not found")

    update_data = workout_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(workout, field, value)

    db.commit()
    db.refresh(workout)
    return workout


@workout_router.delete("/workouts/{workout_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workout(
    workout_id: int,
    db: Session = Depends(get_db),
    current_db_user: User = Depends(get_current_db_user),
):
    """Delete a workout and all its exercise links."""
    workout = db.query(Workouts).filter(Workouts.id == workout_id).first()
    if not workout:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workout not found")

    db.delete(workout)
    db.commit()
    return None


# ============================================================================
# EXERCISES — GET / UPDATE / DELETE
# ============================================================================

@workout_router.get("/exercises/{exercise_id}", response_model=ExerciseResponse)
def get_exercise(
    exercise_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Retrieve a single exercise with its tags."""
    ex = db.query(Exercises).filter(Exercises.id == exercise_id).first()
    if not ex:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exercise not found")

    return {
        "id": ex.id,
        "name": ex.name,
        "description": ex.description,
        "instruction": ex.instruction,
        "is_equipment_needed": ex.is_equipment_needed,
        "video_url": ex.video_url,
        "image_url": ex.image_url,
        "created_at": ex.created_at,
        "tags": [link.tag.name for link in ex.exercise_exer_tags] if ex.exercise_exer_tags else [],
    }


@workout_router.patch("/exercises/{exercise_id}", response_model=ExerciseResponse)
def update_exercise(
    exercise_id: int,
    exercise_data: ExerciseUpdate,
    db: Session = Depends(get_db),
    current_db_user: User = Depends(get_current_db_user),
):
    """Update an exercise's details."""
    ex = db.query(Exercises).filter(Exercises.id == exercise_id).first()
    if not ex:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exercise not found")

    update_data = exercise_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(ex, field, value)

    db.commit()
    db.refresh(ex)

    return {
        "id": ex.id,
        "name": ex.name,
        "description": ex.description,
        "instruction": ex.instruction,
        "is_equipment_needed": ex.is_equipment_needed,
        "video_url": ex.video_url,
        "image_url": ex.image_url,
        "created_at": ex.created_at,
        "tags": [link.tag.name for link in ex.exercise_exer_tags] if ex.exercise_exer_tags else [],
    }


@workout_router.delete("/exercises/{exercise_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_exercise(
    exercise_id: int,
    db: Session = Depends(get_db),
    current_db_user: User = Depends(get_current_db_user),
):
    """Delete an exercise and all its tag/workout links."""
    ex = db.query(Exercises).filter(Exercises.id == exercise_id).first()
    if not ex:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exercise not found")

    db.delete(ex)
    db.commit()
    return None