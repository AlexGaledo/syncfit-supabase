"""Workout API endpoints - Ford"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from datetime import datetime, timedelta, date
from sqlalchemy.orm import Session
from typing import List, Optional, Union
from uuid import UUID

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.dependencies import get_current_db_user
from app.models.item import (
    Exercises, Workouts, Workout_Plans, Exercises_Workouts, Workouts_Workout_Plans,
    Plan_Tags, Workout_Plans_Plan_Tags, Exer_Tags, Exercises_Exer_Tags,
    Workout_Plans_Users, Workout_Logs, Workout_User_Stats, DifficultyLevel
)
from app.schemas.item import (
    ExerciseCreate, ExerciseUpdate, ExerciseResponse,
    WorkoutCreate, WorkoutUpdate, WorkoutResponse,
    WorkoutPlanCreate, WorkoutPlanUpdate, WorkoutPlanResponse,
    ExercisesWorkoutsCreate, ExercisesWorkoutsResponse,
    WorkoutsWorkoutPlansCreate, WorkoutsWorkoutPlansResponse,
    WorkoutPlansUsersCreate, WorkoutPlansUsersResponse, WorkoutPlansUsersUpdate,
    SeederFullWorkoutPlan, CreateFullWorkoutPlan, CreateWorkout, CreateExerciseWorkout,
    CreateFullWorkoutRequest, UpdateFullWorkout, UpdateFullWorkoutExercise,
    FullWorkoutPlanDetailResponse, FullWorkoutDetail, FullExerciseDetail,
    FinishWorkoutLogCreate,
    FinishWorkoutLogResponse, WorkoutLogResponse,
    WorkoutUserStatsMessageResponse, WorkoutUserStatsResponse,
    ExerTagCreate, ExerTagResponse,
    PlanTagCreate, PlanTagResponse,
    ExercisesExerTagsCreate, ExercisesExerTagsResponse,
    WorkoutPlansPlanTagsCreate, WorkoutPlansPlanTagsResponse, AIGenerateRequest
)
from app.schemas.user import UserInfoContextResponse
from app.context_gemini.workout.sys_prompt import build_system_prompt

import os
import json
import importlib.util
import google.generativeai as genai # type: ignore

workout_router = APIRouter(prefix="/workout", tags=["Workout"])

@workout_router.get("/user-info-context", response_model=UserInfoContextResponse)
def get_user_info_context(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_db_user)
):
    """
    Retrieve specific contextual information about the user.
    Includes gender, age (calculated from birthdate), weight, and height.
    """
    age = None
    if current_user.birthdate: # type: ignore
        bdate = current_user.birthdate.date() if hasattr(current_user.birthdate, 'date') else current_user.birthdate # type: ignore
        today = date.today()
        age = today.year - bdate.year - ((today.month, today.day) < (bdate.month, bdate.day))

    weight = None
    height = None
    if current_user.profile: # type: ignore
        weight = current_user.profile.weight # type: ignore
        height = current_user.profile.height # type: ignore

    return UserInfoContextResponse(
        user_id=current_user.id, # type: ignore
        gender=current_user.gender.value if current_user.gender else None, # type: ignore
        age=age,
        weight=weight,
        height=height
    )

@workout_router.get("/test-current-user")
def test_current_user(current_db_user: User = Depends(get_current_db_user)):
    """
    Returns the current user's database object for debugging.
    """
    return current_db_user




# ============================================================================
# EXERCISES — LIST / GET / CREATE / UPDATE / DELETE
# ============================================================================


@workout_router.get("/exercises", response_model=List[ExerciseResponse])
def get_all_exercises(
    name: Optional[str] = None,
    is_equipment_needed: Optional[bool] = None,
    exer_tags: Optional[List[str]] = Query(None),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Retrieve all exercises with optional filtering by name, equipment needs, and tags.
    """
    query = db.query(Exercises)

    if name is not None:
        query = query.filter(Exercises.name.ilike(f"%{name}%"))
        
    if is_equipment_needed is not None:
        query = query.filter(Exercises.is_equipment_needed == is_equipment_needed)
        
    if exer_tags:
        query = query.join(Exercises.exercise_exer_tags).join(Exercises_Exer_Tags.tag).filter(Exer_Tags.name.in_(exer_tags))

    exercises = query.offset(skip).limit(limit).all()
    
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
            "is_by_reps": ex.is_by_reps,
            "is_by_duration": ex.is_by_duration,
            "created_at": ex.created_at,
            "tags": [link.tag.name for link in ex.exercise_exer_tags] if ex.exercise_exer_tags else []
        }
        result.append(ex_dict)
        
    return result


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
        "is_by_reps": ex.is_by_reps,
        "is_by_duration": ex.is_by_duration,
        "created_at": ex.created_at,
        "tags": [link.tag.name for link in ex.exercise_exer_tags] if ex.exercise_exer_tags else [],
    }


@workout_router.post("/exercises", response_model=List[ExerciseResponse], status_code=status.HTTP_201_CREATED)
def create_exercises(
    exercises: List[ExerciseCreate],
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Create one or more new exercises. If an exercise with the same name already exists, reuse it instead of creating a duplicate.
    This is for admin purposes only. Ordinary users should not be creating exercises - they should use the existing library when building workouts.
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


@workout_router.patch("/exercises/{exercise_id}", response_model=ExerciseResponse)
def update_exercise(
    exercise_id: int,
    exercise_data: ExerciseUpdate,
    db: Session = Depends(get_db),
    current_db_user: User = Depends(get_current_db_user),
):
    """
    Update an exercise's metadata.
    These are for admin purposes only. Ordinary users should not be updating exercises - they should use the existing library when building workouts.
    """
    if current_db_user.role.value != "admin": # type: ignore
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can modify exercises")

    ex = db.query(Exercises).filter(Exercises.id == exercise_id).first()
    if not ex:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exercise not found")

    update_data = exercise_data.model_dump(exclude_unset=True)
    update_data.pop("tags", None)  # Prevent standard update from overriding relationship list directly

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
        "is_by_reps": ex.is_by_reps,
        "is_by_duration": ex.is_by_duration,
        "created_at": ex.created_at,
        "tags": [link.tag.name for link in ex.exercise_exer_tags] if ex.exercise_exer_tags else []
    }


@workout_router.delete("/exercises/{exercise_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_exercise(
    exercise_id: int,
    db: Session = Depends(get_db),
    current_db_user: User = Depends(get_current_db_user),
):
    """
    Delete an exercise.
    These are for admin purposes only. Ordinary users should not be deleting exercises - they should use the existing library when building workouts.
    """
    if current_db_user.role.value != "admin": # type: ignore
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can delete exercises")

    ex = db.query(Exercises).filter(Exercises.id == exercise_id).first()
    if not ex:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exercise not found")

    db.delete(ex)
    db.commit()
    return None


# ============================================================================
# WORKOUTS — LIST / GET / POST / UPDATE / DELETE
# ============================================================================

@workout_router.get("/workouts", response_model=List[WorkoutResponse])
def get_all_workouts(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Retrieve all workouts metadata."""
    return db.query(Workouts).offset(skip).limit(limit).all()


@workout_router.post("/workouts/full", response_model=FullWorkoutDetail, status_code=status.HTTP_201_CREATED)
def create_full_workout(
    workout_data: CreateFullWorkoutRequest,
    db: Session = Depends(get_db),
    current_db_user: User = Depends(get_current_db_user),
):
    """
    Creates a new workout, links it to a workout plan, and inserts its exercises.
    """
    # 1. Verify the plan exists and check authorization if necessary
    plan = db.query(Workout_Plans).filter(Workout_Plans.id == workout_data.plan_id).first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workout plan not found")
        
    # Optional authorization check
    if plan.created_by != current_db_user.id and current_db_user.role.value != "admin": # type: ignore
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to alter this workout plan")

    try:
        # 2. Create the workout metadata
        db_workout = Workouts(
            title=workout_data.title,
            description=workout_data.description,
            estimated_duration_minutes=workout_data.estimated_duration_minutes
        )
        db.add(db_workout)
        db.flush() # Flush to get the new workout id

        # 3. Link workout to the workout plan
        db_plan_link = Workouts_Workout_Plans(
            plan_id=workout_data.plan_id,
            workout_id=db_workout.id,
            order_index=workout_data.order_index,
            day_of_week=workout_data.day_of_week
        )
        db.add(db_plan_link)

        # 4. Insert exercises 
        for ex in workout_data.exercises:
            ex_exists = db.query(Exercises).filter(Exercises.id == ex.exercise_id).first()
            if not ex_exists:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Exercise with id {ex.exercise_id} not found")
            
            db_ex_link = Exercises_Workouts(
                workout_id=db_workout.id,
                exercise_id=ex.exercise_id,
                sets=ex.sets,
                reps=ex.reps,
                duration_seconds=ex.duration_seconds,
                rest_duration_seconds=ex.rest_duration_seconds,
                order_index=ex.order_index
            )
            db.add(db_ex_link)
            
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An error occurred: {str(e)}")

    # 5. Return updated full state
    return get_full_workout(workout_id=db_workout.id, db=db, current_user=current_db_user) # type: ignore


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


@workout_router.get("/workouts/{workout_id}/full", response_model=FullWorkoutDetail)
def get_full_workout(
    workout_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Retrieve all details of a single workout, including all details of its associated exercises."""
    workout = db.query(Workouts).filter(Workouts.id == workout_id).first()
    if not workout:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workout not found")

    exercises_links = db.query(Exercises_Workouts).filter(Exercises_Workouts.workout_id == workout_id).all()
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
                is_by_reps=ex_obj.is_by_reps, # type: ignore
                is_by_duration=ex_obj.is_by_duration, # type: ignore
                duration_seconds=ex_link.duration_seconds, # type: ignore
                rest_duration_seconds=ex_link.rest_duration_seconds, # type: ignore
                order_index=ex_link.order_index # type: ignore
            )
        )

    return FullWorkoutDetail(
        workout_id=workout.id, # type: ignore
        title=workout.title, # type: ignore
        description=workout.description, # type: ignore
        estimated_duration_minutes=workout.estimated_duration_minutes, # type: ignore
        day_of_week=None,
        order_index=None,
        exercises=sorted(full_exercises, key=lambda x: x.order_index or 0)
    )


@workout_router.patch("/workouts/{workout_id}", response_model=WorkoutResponse)
def update_workout(
    workout_id: int,
    workout_data: WorkoutUpdate,
    db: Session = Depends(get_db),
    current_db_user: User = Depends(get_current_db_user),
):
    """Update a workout metadata."""
    workout = db.query(Workouts).filter(Workouts.id == workout_id).first()
    if not workout:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workout not found")

    update_data = workout_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(workout, field, value)

    db.commit()
    db.refresh(workout)
    return workout


@workout_router.patch("/workouts/{workout_id}/full", response_model=FullWorkoutDetail)
def update_full_workout(
    workout_id: int,
    workout_data: UpdateFullWorkout,
    db: Session = Depends(get_db),
    current_db_user: User = Depends(get_current_db_user),
):
    """
    Update a workout metadata AND replace all its exercises.
    If 'exercises' is provided, the current exercise list is wiped and fully replaced with the provided list, in the new provided order.
    """
    workout = db.query(Workouts).filter(Workouts.id == workout_id).first()
    if not workout:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workout not found")

    try:
        # Update metadata if provided
        update_data = workout_data.model_dump(exclude_unset=True, exclude={"exercises"})
        for field, value in update_data.items():
            setattr(workout, field, value)

        # Synchronize exercises if the array is provided
        if workout_data.exercises is not None:
            # Drop old list first
            db.query(Exercises_Workouts).filter(Exercises_Workouts.workout_id == workout_id).delete(synchronize_session=False)

            # Insert new list
            for ex in workout_data.exercises:
                ex_exists = db.query(Exercises).filter(Exercises.id == ex.exercise_id).first()
                if not ex_exists:
                    raise HTTPException(status_code=400, detail=f"Exercise with id {ex.exercise_id} not found")
                
                db_ex_link = Exercises_Workouts(
                    workout_id=workout_id,
                    exercise_id=ex.exercise_id,
                    sets=ex.sets,
                    reps=ex.reps,
                    duration_seconds=ex.duration_seconds,
                    rest_duration_seconds=ex.rest_duration_seconds,
                    order_index=ex.order_index
                )
                db.add(db_ex_link)
        
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An error occurred: {str(e)}")

    # Return updated full state
    return get_full_workout(workout_id=workout_id, db=db, current_user=current_db_user) # type: ignore


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
# WORKOUT PLANS — LIST / GET / CREATE / UPDATE / DELETE
# ============================================================================


@workout_router.get("/workout-plans", response_model=List[WorkoutPlanResponse])
def get_workout_plans(
    title: Optional[str] = None,
    difficulty: Optional[DifficultyLevel] = None,
    days_per_week: Optional[int] = None,
    is_preset: Optional[bool] = None,
    is_equipment_needed: Optional[bool] = None,
    plan_tags: Optional[List[str]] = Query(None),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Search and filter workout plans. Returns workout plan information, including tags.
    """
    query = db.query(Workout_Plans)

    if title is not None:
        query = query.filter(Workout_Plans.title.ilike(f"%{title}%"))

    if difficulty is not None:
        query = query.filter(Workout_Plans.difficulty == difficulty)

    if days_per_week is not None:
        query = query.filter(Workout_Plans.days_per_week == days_per_week)

    if is_preset is not None:
        query = query.filter(Workout_Plans.is_preset == is_preset)

    if is_equipment_needed is not None:
        query = query.filter(Workout_Plans.is_equipment_needed == is_equipment_needed)

    if plan_tags:
        query = query.join(Workout_Plans.workout_plan_tags).join(Workout_Plans_Plan_Tags.tag).filter(Plan_Tags.name.in_(plan_tags))

    plans = query.offset(skip).limit(limit).all()
    
    result = []
    for plan in plans:
        plan_dict = {
            "id": plan.id,
            "title": plan.title,
            "description": plan.description,
            "duration_minutes": plan.duration_minutes,
            "difficulty": plan.difficulty,
            "days_per_week": plan.days_per_week,
            "ai_generated": plan.ai_generated,
            "is_preset": plan.is_preset,
            "is_equipment_needed": plan.is_equipment_needed,
            "image_url": plan.image_url,
            "created_by": plan.created_by,
            "created_at": plan.created_at,
            "updated_at": plan.updated_at,
            "tags": [link.tag.name for link in plan.workout_plan_tags] if plan.workout_plan_tags else []
        }
        result.append(plan_dict)

    return result


# ============================================================================
# WORKOUT STATS AND LOGS
# ============================================================================

@workout_router.get("/stats/my-stats", response_model=WorkoutUserStatsMessageResponse)
def get_my_workout_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_db_user)
):
    """
    Retrieve the current user's workout stats.
    If none exist, return default values and a message.
    """
    stats = db.query(Workout_User_Stats).filter(Workout_User_Stats.trainee_id == current_user.id).first()
    if not stats:
        return WorkoutUserStatsMessageResponse(
            message="Workout stats do not exist yet or no workouts done yet.",
            trainee_id=current_user.id, # type: ignore[arg-type]
            total_workouts_done=0,
            current_streak=0,
            longest_streak=0,
            total_minutes_trained=0,
            last_workout_log_id=None,
        )

    return WorkoutUserStatsMessageResponse(
        trainee_id=stats.trainee_id, # type: ignore[arg-type]
        total_workouts_done=stats.total_workouts_done, # type: ignore[arg-type]
        current_streak=stats.current_streak, # type: ignore[arg-type]
        longest_streak=stats.longest_streak, # type: ignore[arg-type]
        total_minutes_trained=stats.total_minutes_trained, # type: ignore[arg-type]
        last_workout_log_id=stats.last_workout_log_id, # type: ignore[arg-type]
    )


@workout_router.post("/logs/finish-workout", response_model=FinishWorkoutLogResponse, status_code=status.HTTP_201_CREATED)
def finish_workout(
    payload: FinishWorkoutLogCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_db_user)
):
    """
    Log a completed workout session and update the user's workout stats.
    """
    if payload.plan_id is None:
        assignment = db.query(Workout_Plans_Users).filter(
            Workout_Plans_Users.trainee_id == current_user.id,
            Workout_Plans_Users.is_active == True
        ).first()
        if not assignment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active workout plan found")
        plan_id = assignment.plan_id
    else:
        plan_id = payload.plan_id

    # Ensure workout is part of the plan
    workout_link = db.query(Workouts_Workout_Plans).filter(
        Workouts_Workout_Plans.plan_id == plan_id,
        Workouts_Workout_Plans.workout_id == payload.workout_id,
    ).first()
    if not workout_link:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Workout is not part of the plan")

    # Compute duration and total exercises
    duration_minutes = int((payload.end_datetime - payload.start_datetime).total_seconds() // 60)
    total_exercises_completed = db.query(Exercises_Workouts).filter(
        Exercises_Workouts.workout_id == payload.workout_id
    ).count()

    # Insert workout log
    log = Workout_Logs(
        trainee_id=current_user.id,
        plan_id=plan_id,
        workout_id=payload.workout_id,
        start_datetime=payload.start_datetime,
        end_datetime=payload.end_datetime,
        duration_minutes=duration_minutes,
        total_exercises_completed=total_exercises_completed,
    )
    db.add(log)
    db.flush()

    # Ensure stats row exists
    stats = db.query(Workout_User_Stats).filter(Workout_User_Stats.trainee_id == current_user.id).first()
    if not stats:
        stats = Workout_User_Stats(trainee_id=current_user.id)
        db.add(stats)
        db.flush()

    # Build schedule (day_of_week: 1=Mon ... 7=Sun)
    schedule_days = db.query(Workouts_Workout_Plans.day_of_week).filter(
        Workouts_Workout_Plans.plan_id == plan_id
    ).distinct().all()
    schedule_set = {row[0] for row in schedule_days if row[0] is not None}

    last_log = None
    if stats.last_workout_log_id is not None:
        last_log = db.query(Workout_Logs).filter(Workout_Logs.id == stats.last_workout_log_id).first()

    current_date = payload.start_datetime.date()

    if not last_log or not schedule_set:
        # First logged workout or no schedule defined
        new_streak = 1
    else:
        last_date = last_log.start_datetime.date()
        if last_date >= current_date:
            new_streak = stats.current_streak or 1
        else:
            missed_scheduled = False
            check_date = last_date + timedelta(days=1)
            while check_date < current_date:
                weekday = check_date.weekday() + 1
                if weekday in schedule_set:
                    missed_scheduled = True
                    break
                check_date += timedelta(days=1)
            current_streak = int(stats.current_streak or 0)  # type: ignore[arg-type]
            new_streak = 1 if missed_scheduled else (current_streak + 1)

    total_workouts_done = int(stats.total_workouts_done or 0) + 1  # type: ignore[arg-type]
    total_minutes_trained = int(stats.total_minutes_trained or 0) + duration_minutes  # type: ignore[arg-type]
    longest_streak = int(stats.longest_streak or 0)  # type: ignore[arg-type]

    new_streak_value = int(new_streak)  # type: ignore[arg-type]

    stats.total_workouts_done = total_workouts_done  # type: ignore[assignment]
    stats.total_minutes_trained = total_minutes_trained  # type: ignore[assignment]
    stats.current_streak = new_streak_value  # type: ignore[assignment]
    if new_streak_value > longest_streak:
        stats.longest_streak = new_streak_value  # type: ignore[assignment]
    stats.last_workout_log_id = log.id

    db.commit()
    db.refresh(stats)

    return FinishWorkoutLogResponse(
        message="Workout log created and stats updated.",
        workout_log=WorkoutLogResponse(
            id=log.id, # type: ignore[arg-type]
            trainee_id=log.trainee_id, # type: ignore[arg-type]
            plan_id=log.plan_id, # type: ignore[arg-type]
            workout_id=log.workout_id, # type: ignore[arg-type]
            start_datetime=log.start_datetime, # type: ignore[arg-type]
            end_datetime=log.end_datetime, # type: ignore[arg-type]
            duration_minutes=log.duration_minutes, # type: ignore[arg-type]
            total_exercises_completed=log.total_exercises_completed, # type: ignore[arg-type]
        ),
        stats=WorkoutUserStatsResponse(
            trainee_id=stats.trainee_id, # type: ignore[arg-type]
            total_workouts_done=stats.total_workouts_done, # type: ignore[arg-type]
            current_streak=stats.current_streak, # type: ignore[arg-type]
            longest_streak=stats.longest_streak, # type: ignore[arg-type]
            total_minutes_trained=stats.total_minutes_trained, # type: ignore[arg-type]
            last_workout_log_id=stats.last_workout_log_id, # type: ignore[arg-type]
        ),
    )


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
                    is_by_reps=ex_obj.is_by_reps, # type: ignore
                    is_by_duration=ex_obj.is_by_duration, # type: ignore
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
        is_preset=plan.is_preset, # type: ignore
        is_equipment_needed=plan.is_equipment_needed, # type: ignore
        image_url=plan.image_url, # type: ignore
        created_by=plan.created_by, # type: ignore
        tags=plan_tags,
        workouts=sorted(full_workouts, key=lambda x: x.order_index)
    )


@workout_router.get("/workout-plans/{plan_id}/schedule")
def get_workout_plan_schedule(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Retrieve the workout schedule for a plan.
    """
    plan = db.query(Workout_Plans).filter(Workout_Plans.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workout plan not found")

    day_name_map = {
        1: "Monday",
        2: "Tuesday",
        3: "Wednesday",
        4: "Thursday",
        5: "Friday",
        6: "Saturday",
        7: "Sunday",
    }

    links = db.query(Workouts_Workout_Plans).filter(Workouts_Workout_Plans.plan_id == plan_id).all()
    schedule = []
    for link in links:
        day_of_week_int = link.day_of_week if link.day_of_week is not None else None
        day_name = "Unknown"
        if day_of_week_int is not None:
            day_name = day_name_map.get(day_of_week_int, "Unknown")  # type: ignore[arg-type]
        schedule.append({
            "workout_id": link.workout_id,
            "workout_title": link.workout.title,
            "day_of_week_int": day_of_week_int, # type: ignore[assignment]
            "day_of_week_string": day_name,
            "order_index": link.order_index,
        })

    return {
        "plan_id": plan.id,
        "days_per_week": plan.days_per_week,
        "schedule": sorted(schedule, key=lambda x: (x["day_of_week_int"] or 0, x["order_index"] or 0)),
    }


@workout_router.get("/workout-plans/today-workout")
def get_today_workout_plan(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_db_user)
):
    """
    Retrieve today's workout for the user's active plan, or the most recent pending workout.
    """
    assignment = db.query(Workout_Plans_Users).filter(
        Workout_Plans_Users.trainee_id == current_user.id,
        Workout_Plans_Users.is_active == True
    ).first()
    if not assignment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active workout plan found")

    plan_id = assignment.plan_id
    links = db.query(Workouts_Workout_Plans).filter(Workouts_Workout_Plans.plan_id == plan_id).all()
    if not links:
        return {
            "workout_id": None,
            "title": "Rest Day",
            "description": None,
            "estimated_duration_minutes": None,
            "day_of_week": None,
            "order_index": None,
            "exercises": [],
            "message": "No workouts are scheduled for this plan.",
        }

    today = datetime.now().date()
    today = date(2026, 4, 19)
    today_weekday = today.weekday() + 1
    today_weekday = 7

    day_name_map = {
        1: "Monday",
        2: "Tuesday",
        3: "Wednesday",
        4: "Thursday",
        5: "Friday",
        6: "Saturday",
        7: "Sunday",
    }

    links_by_day = {}
    for link in links:
        if link.day_of_week is None:
            continue
        links_by_day.setdefault(link.day_of_week, []).append(link)

    for day_links in links_by_day.values():
        day_links.sort(key=lambda l: l.order_index or 0)

    today_links = links_by_day.get(today_weekday)
    if today_links:
        link = today_links[0]
        workout_detail = get_full_workout(workout_id=link.workout_id, db=db, current_user=current_user) # type: ignore
        workout_detail = workout_detail.model_copy(update={
            "day_of_week": link.day_of_week,
            "order_index": link.order_index,
        })
        return workout_detail.model_dump()

    # Find the most recent scheduled day before today
    target_date = None
    target_link = None
    for offset in range(1, 8):
        candidate_date = today - timedelta(days=offset)
        candidate_weekday = candidate_date.weekday() + 1
        candidate_links = links_by_day.get(candidate_weekday)
        if candidate_links:
            target_date = candidate_date
            target_link = candidate_links[0]
            break

    if not target_link or not target_date:
        return {
            "workout_id": None,
            "title": "Rest Day",
            "description": None,
            "estimated_duration_minutes": None,
            "day_of_week": today_weekday,
            "order_index": None,
            "exercises": [],
            "message": "No scheduled workout found for today.",
        }

    # Check if the most recent scheduled workout is already done
    done_log = db.query(Workout_Logs).filter(
        Workout_Logs.trainee_id == current_user.id,
        Workout_Logs.plan_id == plan_id,
        Workout_Logs.workout_id == target_link.workout_id,
        Workout_Logs.start_datetime >= datetime.combine(target_date, datetime.min.time()),
        Workout_Logs.start_datetime <= datetime.combine(target_date, datetime.max.time()),
    ).first()

    if done_log:
        return {
            "workout_id": None,
            "title": "Rest Day",
            "description": None,
            "estimated_duration_minutes": None,
            "day_of_week": today_weekday,
            "order_index": None,
            "exercises": [],
            "message": "No workout scheduled for today. Enjoy your rest day.",
        }

    workout_detail = get_full_workout(workout_id=target_link.workout_id, db=db, current_user=current_user) # type: ignore
    workout_detail = workout_detail.model_copy(update={
        "day_of_week": target_link.day_of_week,
        "order_index": target_link.order_index,
    })

    response = workout_detail.model_dump()
    response["message"] = (
        f"Pending workout from {day_name_map.get(target_link.day_of_week, 'previous scheduled day')}."
    )
    return response


@workout_router.get("/workout-plans/my-workout-plan", response_model=Union[List[FullWorkoutPlanDetailResponse], FullWorkoutPlanDetailResponse])
def get_my_workout_plan(
    all: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_db_user)
):
    """
    Retrieve workout plans assigned to the current user (where the user is trainee).
    Returned object can be the active workout plan or the list of all workout plans assigned to the user (active + inactive) based on the query parameter.

    ### Query Parameters:
    - **all** (bool, optional): 
        - `false` (Default): Returns only the **currently active** workout plan object.
        - `true`: Returns a **list** of all assigned workout plans (Active + Inactive).

    """
    query = db.query(Workout_Plans_Users).filter(
        Workout_Plans_Users.trainee_id == current_user.id
    )

    # Filter by active only if 'all' is False
    if not all:
        query = query.filter(Workout_Plans_Users.is_active == True)

    assignments = query.all()

    if not assignments:
        if not all:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="No active workout plan found for the current user."
            )
        return []

    plans = []
    for assignment in assignments:
        try:
            full_plan = get_full_workout_plan(plan_id=assignment.plan_id, db=db, current_user=current_user) # type: ignore
            plans.append(full_plan)
        except Exception:
            continue

    if not all:
        return plans[0] if plans else None

    return plans


@workout_router.get("/workout-plans/created-by/{user_id}", response_model=List[WorkoutPlanResponse])
def get_workout_plans_created_by_user(
    user_id: UUID,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Retrieve all workout plans metadata created by a specific user. 
    This is to view all plans created by a specific user.
    """
    plans = db.query(Workout_Plans).filter(Workout_Plans.created_by == user_id).offset(skip).limit(limit).all()
    return plans


@workout_router.post("/workout-plans/create-full", response_model=FullWorkoutPlanDetailResponse, status_code=status.HTTP_201_CREATED)
def create_full_workout_plan(
    plan_data: CreateFullWorkoutPlan,
    db: Session = Depends(get_db),
    current_db_user: User = Depends(get_current_db_user)
):
    """
    Creates a complete workout plan including workouts and their associations with existing exercises.
    This endpoint is intended for end users (trainees/trainers) to construct a program using the existing exercise library.
    All operations are performed in a single transaction.
    This does not assign the plan to any user - it only creates the plan and its related workouts. Use the /assign-workout-plan endpoint to link it to a trainee/trainer.
    """
    try:
        # 1. Create the workout plan
        if plan_data.image_url is None:
            plan_data.image_url = "https://assets.gqindia.com/photos/6901d75412ed49c7aea3ce5c/16:9/w_2560%2Cc_limit/work.jpg"
        
        db_plan = Workout_Plans(
            title=plan_data.title,
            description=plan_data.description,
            duration_minutes=plan_data.duration_minutes,
            difficulty=plan_data.difficulty,
            days_per_week=plan_data.days_per_week,
            ai_generated=plan_data.ai_generated,
            is_preset=plan_data.is_preset,
            is_equipment_needed=plan_data.is_equipment_needed,
            image_url=plan_data.image_url,
            created_by=current_db_user.id,
        )
        db.add(db_plan)
        # Flush to assign ID to the new plan
        db.flush()

        # Process plan tags
        plan_tags = plan_data.tags or []
        for tag_name in plan_tags:
            db_tag = db.query(Plan_Tags).filter(Plan_Tags.name == tag_name).first()
            if not db_tag:
                db_tag = Plan_Tags(name=tag_name)
                db.add(db_tag)
                db.flush()
            
            db.add(Workout_Plans_Plan_Tags(plan_id=db_plan.id, tag_id=db_tag.id))
            db.flush()

        # 2. Create workouts and link everything together
        for workout_data in plan_data.workouts:
            db_workout = Workouts(
                title=workout_data.title,
                description=workout_data.description,
                estimated_duration_minutes=workout_data.estimated_duration_minutes
            )
            db.add(db_workout)
            # Flush to assign ID to the new workout
            db.flush()

            # Link workout to plan for the specified day
            db_link = Workouts_Workout_Plans(
                plan_id=db_plan.id,
                workout_id=db_workout.id,
                order_index=workout_data.order_index,
                day_of_week=workout_data.day_of_week
            )
            db.add(db_link)

            # Link exercises to workout
            for ex_workout_data in workout_data.exercises:
                # Ensure exercise exists
                exercise_obj = db.query(Exercises).filter(Exercises.id == ex_workout_data.exercise_id).first()
                if not exercise_obj:
                    raise HTTPException(status_code=404, detail=f"Exercise with ID '{ex_workout_data.exercise_id}' not found.")

                link_data = {
                    "workout_id": db_workout.id,
                    "exercise_id": exercise_obj.id,
                    "order_index": ex_workout_data.order_index,
                    "sets": ex_workout_data.sets,
                    "reps": ex_workout_data.reps,
                    "duration_seconds": ex_workout_data.duration_seconds,
                    "rest_duration_seconds": ex_workout_data.rest_duration_seconds,
                }
                db_ex_link = Exercises_Workouts(**link_data)
                db.add(db_ex_link)
        
        db.commit()
    
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An error occurred: {str(e)}")

    # Delegate the response building to the existing endpoint function
    return get_full_workout_plan(plan_id=db_plan.id, db=db, current_user=current_db_user) # type: ignore


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
    Delete a workout plan and associated workouts. Only the creator or an admin may do this.
    """
    plan = db.query(Workout_Plans).filter(Workout_Plans.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workout plan not found")

    if plan.created_by != current_db_user.id and current_db_user.role.value != "admin": #type:ignore
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only delete your own workout plans")

    associated_workouts = db.query(Workouts).join(Workouts_Workout_Plans).filter(
        Workouts_Workout_Plans.plan_id == plan_id
    ).all()
    
    for w in associated_workouts:
        db.delete(w) 

    db.delete(plan)
    db.commit()
    return None


@workout_router.post("/workout-plans/ai-generate-full", status_code=status.HTTP_200_OK)
def ai_generate_full_workout_plan(
    request: AIGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_db_user)
):
    """
    Generate a full workout plan using the Gemini API based on user context and prompt.
    Returns JSON matching the CreateFullWorkoutPlan schema.
    This only returns the JSON data. To save it to the database, use the /workout-plans/create-full endpoint with the returned JSON as the payload. To assign the generated plan to a user, use the /workout-plans/assign endpoint with the created plan ID and user ID.
    """
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="GEMINI_API_KEY is not configured"
        )

    # Get user context
    user_context = get_user_info_context(db, current_user)
    
    # Read JSON context files
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    gemini_dir = os.path.join(base_dir, "context_gemini", "workout")
    
    try:
        sys_prompt = build_system_prompt(user_context, gemini_dir)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read context files or build system prompt: {str(e)}"
        )

    import google.api_core.exceptions

    genai.configure(api_key=gemini_key) # type: ignore
    # Using gemini-3.1-flash-lite based on best available rate limits (15 RPM / 500 RPD)
    model = genai.GenerativeModel('gemini-3.1-flash-lite-preview', system_instruction=sys_prompt) # type: ignore
    
    try:
        response = model.generate_content(
            request.prompt,
            generation_config=genai.types.GenerationConfig( # type: ignore
                response_mime_type="application/json",
            ), 
        )
    except google.api_core.exceptions.ResourceExhausted:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Gemini API rate limit exceeded. Please wait a moment and try again."
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gemini API error: {str(e)}"
        )
    
    try:
        raw_text = response.text.strip()
        # Find the first '{' or '[' and the last '}' or ']'
        start_idx = raw_text.find('{')
        if start_idx == -1:
            start_idx = raw_text.find('[')
            
        end_idx = raw_text.rfind('}')
        if end_idx == -1 or (raw_text.rfind(']') > end_idx):
            end_idx = raw_text.rfind(']')
            
        if start_idx != -1 and end_idx != -1:
            raw_text = raw_text[start_idx:end_idx+1]
            
        data = json.loads(raw_text)
        return data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to parse Gemini response: {response.text}"
        )


@workout_router.post("/workout-plans/seed-full", status_code=status.HTTP_201_CREATED)
def seed_full_workout_plan(
    plan_data: SeederFullWorkoutPlan,
    db: Session = Depends(get_db),
    current_db_user: User = Depends(get_current_db_user)
):
    """
    Seeds a complete workout plan, including exercises, workouts, and their associations.
    This is a generic seeder that accepts a JSON payload with the full plan structure.
    All operations are performed in a single transaction.
    This is for admin use only.
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


# ============================================================================
# WORKOUT PLANS TO USERS ASSIGNMENTS  — LIST / GET / CREATE / UPDATE / DELETE
# ============================================================================

@workout_router.get("/workout-plans/assign", response_model=List[WorkoutPlansUsersResponse])
def get_all_workout_plan_assignments(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_db_user)
):
    """
    Retrieve all workout plan user assignments. (Admin only)
    """
    if current_user.role.value != "admin": # type: ignore
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can view all assignments")
    return db.query(Workout_Plans_Users).offset(skip).limit(limit).all()


@workout_router.get("/workout-plans/assign/{assignment_id}", response_model=WorkoutPlansUsersResponse)
def get_workout_plan_assignment(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_db_user)
):
    """
    Retrieve a single workout plan user assignment.
    """
    assignment = db.query(Workout_Plans_Users).filter(Workout_Plans_Users.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workout plan assignment not found")

    # Authorize: Only the trainee, the assigned trainer, or an admin can view
    if current_user.role.value != "admin" and current_user.id != assignment.trainee_id and current_user.id != assignment.trainer_id: # type: ignore
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view this assignment")

    return assignment


@workout_router.post("/workout-plans/assign", response_model=WorkoutPlansUsersResponse, status_code=status.HTTP_201_CREATED)
def assign_workout_plan_to_user(
    assignment: WorkoutPlansUsersCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_db_user)
):
    """
    Assign a workout plan to a trainee, and optionally a trainer.
    Ensures that only one workout plan can be active for a trainee at any time.
    """
    # Check if the plan and user exist
    plan = db.query(Workout_Plans).filter(Workout_Plans.id == assignment.plan_id).first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workout plan not found")
    
    trainee = db.query(User).filter(User.id == assignment.trainee_id).first()
    if not trainee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trainee not found")

    if assignment.trainer_id:
        trainer = db.query(User).filter(User.id == assignment.trainer_id).first()
        if not trainer:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trainer not found")

    # If the new assignment is to be active, deactivate any existing active plans for the trainee
    if assignment.is_active:
        existing_active_assignments = db.query(Workout_Plans_Users).filter(
            Workout_Plans_Users.trainee_id == assignment.trainee_id,
            Workout_Plans_Users.is_active == True
        ).all()
        for active_assignment in existing_active_assignments:
            active_assignment.is_active = False # type: ignore
            db.add(active_assignment)

    # Create the new assignment
    new_assignment = Workout_Plans_Users(**assignment.model_dump())
    db.add(new_assignment)
    db.commit()
    db.refresh(new_assignment)
    
    return new_assignment


@workout_router.patch("/workout-plans/assign/{assignment_id}", response_model=WorkoutPlansUsersResponse)
def update_workout_plan_assignment(
    assignment_id: int,
    assignment_update: WorkoutPlansUsersUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_db_user)
):
    """
    Update a workout plan user assignment.
    """
    assignment = db.query(Workout_Plans_Users).filter(Workout_Plans_Users.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workout plan assignment not found")

    # Authorize: Only the trainee, the assigned trainer, or an admin can update
    if current_user.role.value != "admin" and current_user.id != assignment.trainee_id and current_user.id != assignment.trainer_id: # type: ignore
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to edit this assignment")

    if assignment_update.is_active is True:
        # Prevent multiple active assignments for the same trainee
        existing_active_assignments = db.query(Workout_Plans_Users).filter(
            Workout_Plans_Users.trainee_id == assignment.trainee_id,
            Workout_Plans_Users.is_active == True,
            Workout_Plans_Users.id != assignment.id
        ).all()
        for active_assignment in existing_active_assignments:
            active_assignment.is_active = False # type: ignore
            db.add(active_assignment)

    update_data = assignment_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(assignment, field, value)

    db.commit()
    db.refresh(assignment)
    return assignment


@workout_router.delete("/workout-plans/assign/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workout_plan_assignment(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_db_user)
):
    """
    Delete a workout plan user assignment.
    """
    assignment = db.query(Workout_Plans_Users).filter(Workout_Plans_Users.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workout plan assignment not found")

    # Authorize: Only the trainee, the assigned trainer, or an admin can delete
    if current_user.role.value != "admin" and current_user.id != assignment.trainee_id and current_user.id != assignment.trainer_id: # type: ignore
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this assignment")

    db.delete(assignment)
    db.commit()
    return None




# ============================================================================
# EXERCISE AND WORKOUT PLAN TAGS — LIST / GET / CREATE / DELETE
# ============================================================================


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
    Create multiple exercise tags using a list of tag names. See exer_tags.json for sample input.
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


@workout_router.get("/exer-tags/{tag_id}", response_model=ExerTagResponse)
def get_exer_tag(
    tag_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Retrieve a single exercise tag."""
    tag = db.query(Exer_Tags).filter(Exer_Tags.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exercise tag not found")
    return tag


@workout_router.delete("/exer-tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_exer_tag(
    tag_id: int,
    db: Session = Depends(get_db),
    current_db_user: User = Depends(get_current_db_user)
):
    """Delete an exercise tag. (Admin only)"""
    if current_db_user.role.value != "admin": # type: ignore
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can delete exercise tags")
        
    tag = db.query(Exer_Tags).filter(Exer_Tags.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exercise tag not found")
        
    db.delete(tag)
    db.commit()
    return None


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
    Create multiple plan tags using a list of tag names. See plan_tags.json for sample input.
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


@workout_router.get("/plan-tags/{tag_id}", response_model=PlanTagResponse)
def get_plan_tag(
    tag_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Retrieve a single plan tag."""
    tag = db.query(Plan_Tags).filter(Plan_Tags.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan tag not found")
    return tag


@workout_router.delete("/plan-tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_plan_tag(
    tag_id: int,
    db: Session = Depends(get_db),
    current_db_user: User = Depends(get_current_db_user)
):
    """Delete a plan tag. (Admin only)"""
    if current_db_user.role.value != "admin": # type: ignore
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can delete plan tags")
        
    tag = db.query(Plan_Tags).filter(Plan_Tags.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan tag not found")
        
    db.delete(tag)
    db.commit()
    return None


@workout_router.post("/exer-tags/link-to-exercise", response_model=ExercisesExerTagsResponse, status_code=status.HTTP_201_CREATED)
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


@workout_router.post("/plan-tags/link-to-workout-plan", response_model=WorkoutPlansPlanTagsResponse, status_code=status.HTTP_201_CREATED)
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

