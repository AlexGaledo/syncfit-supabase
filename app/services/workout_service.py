"""Workout domain logic. Routers stay thin and delegate here."""
from datetime import datetime, timedelta, date
from typing import Any, List, Optional, Union
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.item import (
    Exercises,
    Workouts,
    Workout_Plans,
    Exercises_Workouts,
    Workouts_Workout_Plans,
    Plan_Tags,
    Workout_Plans_Plan_Tags,
    Exer_Tags,
    Exercises_Exer_Tags,
    Workout_Plans_Users,
    Workout_Logs,
    Workout_User_Stats,
    DifficultyLevel,
)
from app.schemas.item import (
    ExerciseCreate,
    ExerciseUpdate,
    WorkoutUpdate,
    WorkoutPlanUpdate,
    WorkoutPlansUsersCreate,
    WorkoutPlansUsersUpdate,
    SeederFullWorkoutPlan,
    CreateFullWorkoutPlan,
    CreateFullWorkoutRequest,
    UpdateFullWorkout,
    FullWorkoutPlanDetailResponse,
    FullWorkoutDetail,
    FullExerciseDetail,
    FinishWorkoutLogCreate,
    FinishWorkoutLogResponse,
    WorkoutLogResponse,
    WorkoutUserStatsMessageResponse,
    WorkoutUserStatsResponse,
    ExerTagCreate,
    PlanTagCreate,
    ExercisesExerTagsCreate,
    WorkoutPlansPlanTagsCreate,
)
from app.schemas.user import UserInfoContextResponse


# ============================================================================
# USER CONTEXT
# ============================================================================

def get_user_info_context(db: Session, current_user: User) -> UserInfoContextResponse:
    age = None
    if current_user.birthdate:  # type: ignore
        bdate = current_user.birthdate.date() if hasattr(current_user.birthdate, 'date') else current_user.birthdate  # type: ignore
        today = date.today()
        age = today.year - bdate.year - ((today.month, today.day) < (bdate.month, bdate.day))

    weight = None
    height = None
    if current_user.profile:  # type: ignore
        weight = current_user.profile.weight  # type: ignore
        height = current_user.profile.height  # type: ignore

    return UserInfoContextResponse(
        user_id=current_user.id,  # type: ignore
        gender=current_user.gender.value if current_user.gender else None,  # type: ignore
        age=age,
        weight=weight,
        height=height,
    )


# ============================================================================
# EXERCISES
# ============================================================================

def list_exercises(
    db: Session,
    name: Optional[str],
    is_equipment_needed: Optional[bool],
    exer_tags: Optional[List[str]],
    skip: int,
    limit: int,
) -> List[dict]:
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
            "tags": [link.tag.name for link in ex.exercise_exer_tags] if ex.exercise_exer_tags else [],
        }
        result.append(ex_dict)

    return result


def get_exercise(db: Session, exercise_id: int) -> dict:
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


def create_exercises(db: Session, exercises: List[ExerciseCreate]) -> List[Exercises]:
    created_exercises = []
    for exercise_data in exercises:
        ex_dump = exercise_data.model_dump()
        ex_tags = ex_dump.pop("tags", []) or []

        existing_exercise = db.query(Exercises).filter(Exercises.name == exercise_data.name).first()
        if existing_exercise:
            db_exercise = existing_exercise
        else:
            db_exercise = Exercises(**ex_dump)
            db.add(db_exercise)
            db.flush()

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


def update_exercise(
    db: Session,
    exercise_id: int,
    exercise_data: ExerciseUpdate,
    current_db_user: User,
) -> dict:
    if current_db_user.role.value != "admin":  # type: ignore
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can modify exercises")

    ex = db.query(Exercises).filter(Exercises.id == exercise_id).first()
    if not ex:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exercise not found")

    update_data = exercise_data.model_dump(exclude_unset=True)
    update_data.pop("tags", None)

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
        "tags": [link.tag.name for link in ex.exercise_exer_tags] if ex.exercise_exer_tags else [],
    }


def delete_exercise(db: Session, exercise_id: int, current_db_user: User) -> None:
    if current_db_user.role.value != "admin":  # type: ignore
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can delete exercises")

    ex = db.query(Exercises).filter(Exercises.id == exercise_id).first()
    if not ex:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exercise not found")

    db.delete(ex)
    db.commit()


# ============================================================================
# WORKOUTS
# ============================================================================

def list_workouts(db: Session, skip: int, limit: int) -> List[Workouts]:
    return db.query(Workouts).offset(skip).limit(limit).all()


def get_workout(db: Session, workout_id: int) -> Workouts:
    workout = db.query(Workouts).filter(Workouts.id == workout_id).first()
    if not workout:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workout not found")
    return workout


def get_full_workout(db: Session, workout_id: int) -> FullWorkoutDetail:
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
                sets=ex_link.sets,  # type: ignore
                reps=ex_link.reps,  # type: ignore
                is_by_reps=ex_obj.is_by_reps,  # type: ignore
                is_by_duration=ex_obj.is_by_duration,  # type: ignore
                duration_seconds=ex_link.duration_seconds,  # type: ignore
                rest_duration_seconds=ex_link.rest_duration_seconds,  # type: ignore
                order_index=ex_link.order_index,  # type: ignore
            )
        )

    return FullWorkoutDetail(
        workout_id=workout.id,  # type: ignore
        title=workout.title,  # type: ignore
        description=workout.description,  # type: ignore
        estimated_duration_minutes=workout.estimated_duration_minutes,  # type: ignore
        day_of_week=None,
        order_index=None,
        exercises=sorted(full_exercises, key=lambda x: x.order_index or 0),
    )


def create_full_workout(
    db: Session,
    workout_data: CreateFullWorkoutRequest,
    current_db_user: User,
) -> FullWorkoutDetail:
    plan = db.query(Workout_Plans).filter(Workout_Plans.id == workout_data.plan_id).first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workout plan not found")

    if plan.created_by != current_db_user.id and current_db_user.role.value != "admin":  # type: ignore
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to alter this workout plan")

    try:
        db_workout = Workouts(
            title=workout_data.title,
            description=workout_data.description,
            estimated_duration_minutes=workout_data.estimated_duration_minutes,
        )
        db.add(db_workout)
        db.flush()

        db_plan_link = Workouts_Workout_Plans(
            plan_id=workout_data.plan_id,
            workout_id=db_workout.id,
            order_index=workout_data.order_index,
            day_of_week=workout_data.day_of_week,
        )
        db.add(db_plan_link)

        for ex in workout_data.exercises:
            ex_exists = db.query(Exercises).filter(Exercises.id == ex.exercise_id).first()
            if not ex_exists:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Exercise with id {ex.exercise_id} not found",
                )

            db_ex_link = Exercises_Workouts(
                workout_id=db_workout.id,
                exercise_id=ex.exercise_id,
                sets=ex.sets,
                reps=ex.reps,
                duration_seconds=ex.duration_seconds,
                rest_duration_seconds=ex.rest_duration_seconds,
                order_index=ex.order_index,
            )
            db.add(db_ex_link)

        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}",
        )

    return get_full_workout(db=db, workout_id=db_workout.id)  # type: ignore


def update_workout(db: Session, workout_id: int, workout_data: WorkoutUpdate) -> Workouts:
    workout = db.query(Workouts).filter(Workouts.id == workout_id).first()
    if not workout:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workout not found")

    update_data = workout_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(workout, field, value)

    db.commit()
    db.refresh(workout)
    return workout


def update_full_workout(
    db: Session,
    workout_id: int,
    workout_data: UpdateFullWorkout,
) -> FullWorkoutDetail:
    workout = db.query(Workouts).filter(Workouts.id == workout_id).first()
    if not workout:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workout not found")

    try:
        update_data = workout_data.model_dump(exclude_unset=True, exclude={"exercises"})
        for field, value in update_data.items():
            setattr(workout, field, value)

        if workout_data.exercises is not None:
            db.query(Exercises_Workouts).filter(Exercises_Workouts.workout_id == workout_id).delete(synchronize_session=False)

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
                    order_index=ex.order_index,
                )
                db.add(db_ex_link)

        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}",
        )

    return get_full_workout(db=db, workout_id=workout_id)  # type: ignore


def delete_workout(db: Session, workout_id: int) -> None:
    workout = db.query(Workouts).filter(Workouts.id == workout_id).first()
    if not workout:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workout not found")

    db.delete(workout)
    db.commit()


# ============================================================================
# WORKOUT PLANS
# ============================================================================

def list_workout_plans(
    db: Session,
    title: Optional[str],
    difficulty: Optional[DifficultyLevel],
    days_per_week: Optional[int],
    is_preset: Optional[bool],
    is_equipment_needed: Optional[bool],
    plan_tags: Optional[List[str]],
    skip: int,
    limit: int,
) -> List[dict]:
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
            "tags": [link.tag.name for link in plan.workout_plan_tags] if plan.workout_plan_tags else [],
        }
        result.append(plan_dict)

    return result


def get_full_workout_plan(db: Session, plan_id: int) -> FullWorkoutPlanDetailResponse:
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
                    sets=ex_link.sets,  # type: ignore
                    reps=ex_link.reps,  # type: ignore
                    is_by_reps=ex_obj.is_by_reps,  # type: ignore
                    is_by_duration=ex_obj.is_by_duration,  # type: ignore
                    duration_seconds=ex_link.duration_seconds,  # type: ignore
                    rest_duration_seconds=ex_link.rest_duration_seconds,  # type: ignore
                    order_index=ex_link.order_index,  # type: ignore
                )
            )

        full_workouts.append(
            FullWorkoutDetail(
                workout_id=workout_obj.id,
                title=workout_obj.title,
                description=workout_obj.description,
                estimated_duration_minutes=workout_obj.estimated_duration_minutes,
                day_of_week=link.day_of_week,  # type: ignore
                order_index=link.order_index,  # type: ignore
                exercises=sorted(full_exercises, key=lambda x: x.order_index or 0),
            )
        )

    plan_tags = [link.tag.name for link in plan.workout_plan_tags] if plan.workout_plan_tags else []

    return FullWorkoutPlanDetailResponse(
        plan_id=plan.id,  # type: ignore
        title=plan.title,  # type: ignore
        description=plan.description,  # type: ignore
        duration_minutes=plan.duration_minutes,  # type: ignore
        difficulty=plan.difficulty,  # type: ignore
        days_per_week=plan.days_per_week,  # type: ignore
        ai_generated=plan.ai_generated,  # type: ignore
        is_preset=plan.is_preset,  # type: ignore
        is_equipment_needed=plan.is_equipment_needed,  # type: ignore
        image_url=plan.image_url,  # type: ignore
        created_by=plan.created_by,  # type: ignore
        tags=plan_tags,
        workouts=sorted(full_workouts, key=lambda x: x.order_index),
    )


def get_my_schedule(db: Session, current_user: User) -> dict:
    assignment = db.query(Workout_Plans_Users).filter(
        Workout_Plans_Users.trainee_id == current_user.id,
        Workout_Plans_Users.is_active == True,
    ).first()

    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active workout plan found for the current user.",
        )

    plan_id = assignment.plan_id
    plan = db.query(Workout_Plans).filter(Workout_Plans.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workout plan not found")

    now_aware = datetime.now().astimezone()
    start_of_week = now_aware.date() - timedelta(days=now_aware.weekday())
    start_of_week_dt = datetime.combine(start_of_week, datetime.min.time()).replace(tzinfo=now_aware.tzinfo)
    end_of_week_dt = start_of_week_dt + timedelta(days=7)

    week_logs = db.query(Workout_Logs).filter(
        Workout_Logs.trainee_id == current_user.id,
        Workout_Logs.plan_id == plan_id,
        Workout_Logs.start_datetime >= start_of_week_dt,
        Workout_Logs.start_datetime < end_of_week_dt,
    ).all()

    logged_workout_ids = {log.workout_id for log in week_logs if log.workout_id is not None}
    days_done_this_week = len({log.start_datetime.date() for log in week_logs})

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

        is_done = link.workout_id in logged_workout_ids

        schedule.append({
            "workout_id": link.workout_id,
            "workout_title": link.workout.title,
            "day_of_week_int": day_of_week_int,  # type: ignore[assignment]
            "day_of_week_string": day_name,
            "order_index": link.order_index,
            "is_done": is_done,
        })

    return {
        "plan_id": plan.id,
        "days_per_week": plan.days_per_week,
        "days_done_this_week": days_done_this_week,
        "schedule": sorted(schedule, key=lambda x: (x["day_of_week_int"] or 0, x["order_index"] or 0)),
    }


def get_today_workout(db: Session, current_user: User) -> dict:
    assignment = db.query(Workout_Plans_Users).filter(
        Workout_Plans_Users.trainee_id == current_user.id,
        Workout_Plans_Users.is_active == True,
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
    today_weekday = today.weekday() + 1

    day_name_map = {
        1: "Monday",
        2: "Tuesday",
        3: "Wednesday",
        4: "Thursday",
        5: "Friday",
        6: "Saturday",
        7: "Sunday",
    }

    links_by_day: dict = {}
    for link in links:
        if link.day_of_week is None:
            continue
        links_by_day.setdefault(link.day_of_week, []).append(link)

    for day_links in links_by_day.values():
        day_links.sort(key=lambda l: l.order_index or 0)

    today_links = links_by_day.get(today_weekday)

    start_of_week = today - timedelta(days=today.weekday())
    start_of_week_dt = datetime.combine(start_of_week, datetime.min.time())

    if today_links:
        link = today_links[0]

        todays_done_log = db.query(Workout_Logs).filter(
            Workout_Logs.trainee_id == current_user.id,
            Workout_Logs.plan_id == plan_id,
            Workout_Logs.workout_id == link.workout_id,
            Workout_Logs.start_datetime >= start_of_week_dt,
        ).first()

        if todays_done_log:
            return {
                "workout_id": None,
                "title": "Rest Day",
                "description": None,
                "estimated_duration_minutes": None,
                "day_of_week": today_weekday,
                "order_index": None,
                "exercises": [],
                "message": "You have already completed today's workout. Enjoy your rest!",
            }

        workout_detail = get_full_workout(db=db, workout_id=link.workout_id)  # type: ignore
        workout_detail = workout_detail.model_copy(update={
            "day_of_week": link.day_of_week,
            "order_index": link.order_index,
        })
        return workout_detail.model_dump()

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

    done_log = db.query(Workout_Logs).filter(
        Workout_Logs.trainee_id == current_user.id,
        Workout_Logs.plan_id == plan_id,
        Workout_Logs.workout_id == target_link.workout_id,
        Workout_Logs.start_datetime >= min(start_of_week_dt, datetime.combine(target_date, datetime.min.time())),
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

    workout_detail = get_full_workout(db=db, workout_id=target_link.workout_id)  # type: ignore
    workout_detail = workout_detail.model_copy(update={
        "day_of_week": target_link.day_of_week,
        "order_index": target_link.order_index,
    })

    response = workout_detail.model_dump()
    response["message"] = (
        f"Pending workout from {day_name_map.get(target_link.day_of_week, 'previous scheduled day')}."
    )
    return response


def get_my_workout_plan(
    db: Session,
    current_user: User,
    all: bool,
) -> Union[List[FullWorkoutPlanDetailResponse], FullWorkoutPlanDetailResponse, None, list]:
    query = db.query(Workout_Plans_Users).filter(
        Workout_Plans_Users.trainee_id == current_user.id
    )

    if not all:
        query = query.filter(Workout_Plans_Users.is_active == True)

    assignments = query.all()

    if not assignments:
        if not all:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active workout plan found for the current user.",
            )
        return []

    plans = []
    for assignment in assignments:
        try:
            full_plan = get_full_workout_plan(db=db, plan_id=assignment.plan_id)  # type: ignore
            plans.append(full_plan)
        except Exception:
            continue

    if not all:
        return plans[0] if plans else None

    return plans


def list_plans_created_by_user(
    db: Session,
    user_id: UUID,
    skip: int,
    limit: int,
) -> List[Workout_Plans]:
    return db.query(Workout_Plans).filter(Workout_Plans.created_by == user_id).offset(skip).limit(limit).all()


def create_full_workout_plan(
    db: Session,
    plan_data: CreateFullWorkoutPlan,
    current_db_user: User,
) -> FullWorkoutPlanDetailResponse:
    try:
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
        db.flush()

        plan_tags = plan_data.tags or []
        for tag_name in plan_tags:
            db_tag = db.query(Plan_Tags).filter(Plan_Tags.name == tag_name).first()
            if not db_tag:
                db_tag = Plan_Tags(name=tag_name)
                db.add(db_tag)
                db.flush()

            db.add(Workout_Plans_Plan_Tags(plan_id=db_plan.id, tag_id=db_tag.id))
            db.flush()

        for workout_data in plan_data.workouts:
            db_workout = Workouts(
                title=workout_data.title,
                description=workout_data.description,
                estimated_duration_minutes=workout_data.estimated_duration_minutes,
            )
            db.add(db_workout)
            db.flush()

            db_link = Workouts_Workout_Plans(
                plan_id=db_plan.id,
                workout_id=db_workout.id,
                order_index=workout_data.order_index,
                day_of_week=workout_data.day_of_week,
            )
            db.add(db_link)

            for ex_workout_data in workout_data.exercises:
                exercise_obj = db.query(Exercises).filter(Exercises.id == ex_workout_data.exercise_id).first()
                if not exercise_obj:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Exercise with ID '{ex_workout_data.exercise_id}' not found.",
                    )

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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}",
        )

    return get_full_workout_plan(db=db, plan_id=db_plan.id)  # type: ignore


def update_workout_plan(
    db: Session,
    plan_id: int,
    plan_data: WorkoutPlanUpdate,
    current_db_user: User,
) -> Workout_Plans:
    plan = db.query(Workout_Plans).filter(Workout_Plans.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workout plan not found")

    if plan.created_by != current_db_user.id and current_db_user.role.value != "admin":  # type:ignore
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only update your own workout plans")

    update_data = plan_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(plan, field, value)

    db.commit()
    db.refresh(plan)
    return plan


def delete_workout_plan(db: Session, plan_id: int, current_db_user: User) -> None:
    plan = db.query(Workout_Plans).filter(Workout_Plans.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workout plan not found")

    if plan.created_by != current_db_user.id and current_db_user.role.value != "admin":  # type:ignore
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only delete your own workout plans")

    associated_workouts = db.query(Workouts).join(Workouts_Workout_Plans).filter(
        Workouts_Workout_Plans.plan_id == plan_id
    ).all()

    for w in associated_workouts:
        db.delete(w)

    db.delete(plan)
    db.commit()


def seed_full_workout_plan(
    db: Session,
    plan_data: SeederFullWorkoutPlan,
    current_db_user: User,
) -> dict:
    try:
        created_exercises = {}
        for exercise_data in plan_data.exercises:
            ex_dump = exercise_data.model_dump()
            ex_tags = ex_dump.pop("tags", []) or []

            db_exercise = db.query(Exercises).filter(Exercises.name == exercise_data.name).first()
            if not db_exercise:
                db_exercise = Exercises(**ex_dump)
                db.add(db_exercise)
                db.flush()

            for tag_name in ex_tags:
                db_tag = db.query(Exer_Tags).filter(Exer_Tags.name == tag_name).first()
                if not db_tag:
                    db_tag = Exer_Tags(name=tag_name)
                    db.add(db_tag)
                    db.flush()

                link_exists = db.query(Exercises_Exer_Tags).filter_by(exercise_id=db_exercise.id, tag_id=db_tag.id).first()
                if not link_exists:
                    db_ex_tag_link = Exercises_Exer_Tags(exercise_id=db_exercise.id, tag_id=db_tag.id)
                    db.add(db_ex_tag_link)

            created_exercises[exercise_data.name] = db_exercise

        db.flush()

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
            db.flush()

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

        for workout_data in plan_info.workouts:
            db_workout = db.query(Workouts).filter(Workouts.title == workout_data.title).first()
            if not db_workout:
                db_workout = Workouts(
                    title=workout_data.title,
                    description=workout_data.description,
                    estimated_duration_minutes=workout_data.estimated_duration_minutes,
                )
                db.add(db_workout)
                db.flush()

            link_exists = db.query(Workouts_Workout_Plans).filter_by(
                plan_id=db_plan.id,
                workout_id=db_workout.id,
                day_of_week=workout_data.day_of_week,
            ).first()
            if not link_exists:
                db_link = Workouts_Workout_Plans(
                    plan_id=db_plan.id,
                    workout_id=db_workout.id,
                    order_index=workout_data.order_index,
                    day_of_week=workout_data.day_of_week,
                )
                db.add(db_link)

            for ex_workout_data in workout_data.exercises:
                exercise_obj = created_exercises.get(ex_workout_data.exercise_name)
                if not exercise_obj:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Exercise '{ex_workout_data.exercise_name}' not found in provided list.",
                    )

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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}",
        )

    db.refresh(db_plan)
    return {"message": f"Workout plan '{plan_info.title}' seeded successfully."}


# ============================================================================
# WORKOUT PLAN ASSIGNMENTS
# ============================================================================

def list_assignments(
    db: Session,
    skip: int,
    limit: int,
    current_user: User,
) -> List[Workout_Plans_Users]:
    if current_user.role.value != "admin":  # type: ignore
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can view all assignments")
    return db.query(Workout_Plans_Users).offset(skip).limit(limit).all()


def get_assignment(
    db: Session,
    assignment_id: int,
    current_user: User,
) -> Workout_Plans_Users:
    assignment = db.query(Workout_Plans_Users).filter(Workout_Plans_Users.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workout plan assignment not found")

    if current_user.role.value != "admin" and current_user.id != assignment.trainee_id and current_user.id != assignment.trainer_id:  # type: ignore
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view this assignment")

    return assignment


def assign_workout_plan(
    db: Session,
    assignment: WorkoutPlansUsersCreate,
    current_user: User,
) -> Workout_Plans_Users:
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

    existing_assignment = db.query(Workout_Plans_Users).filter(
        Workout_Plans_Users.trainee_id == assignment.trainee_id,
        Workout_Plans_Users.plan_id == assignment.plan_id,
    ).first()

    if assignment.is_active:
        existing_active_assignments = db.query(Workout_Plans_Users).filter(
            Workout_Plans_Users.trainee_id == assignment.trainee_id,
            Workout_Plans_Users.is_active == True,
        ).all()
        for active_assignment in existing_active_assignments:
            if existing_assignment and active_assignment.id == existing_assignment.id:  # type: ignore
                continue
            active_assignment.is_active = False  # type: ignore
            db.add(active_assignment)

    if existing_assignment:
        existing_assignment.is_active = assignment.is_active  # type: ignore
        existing_assignment.trainer_id = assignment.trainer_id  # type: ignore
        result_assignment = existing_assignment
    else:
        result_assignment = Workout_Plans_Users(**assignment.model_dump())

    db.add(result_assignment)
    db.commit()
    db.refresh(result_assignment)

    return result_assignment


def update_assignment(
    db: Session,
    assignment_id: int,
    assignment_update: WorkoutPlansUsersUpdate,
    current_user: User,
) -> Workout_Plans_Users:
    assignment = db.query(Workout_Plans_Users).filter(Workout_Plans_Users.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workout plan assignment not found")

    if current_user.role.value != "admin" and current_user.id != assignment.trainee_id and current_user.id != assignment.trainer_id:  # type: ignore
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to edit this assignment")

    if assignment_update.is_active is True:
        existing_active_assignments = db.query(Workout_Plans_Users).filter(
            Workout_Plans_Users.trainee_id == assignment.trainee_id,
            Workout_Plans_Users.is_active == True,
            Workout_Plans_Users.id != assignment.id,
        ).all()
        for active_assignment in existing_active_assignments:
            active_assignment.is_active = False  # type: ignore
            db.add(active_assignment)

    update_data = assignment_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(assignment, field, value)

    db.commit()
    db.refresh(assignment)
    return assignment


def delete_assignment(
    db: Session,
    assignment_id: int,
    current_user: User,
) -> None:
    assignment = db.query(Workout_Plans_Users).filter(Workout_Plans_Users.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workout plan assignment not found")

    if current_user.role.value != "admin" and current_user.id != assignment.trainee_id and current_user.id != assignment.trainer_id:  # type: ignore
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this assignment")

    db.delete(assignment)
    db.commit()


# ============================================================================
# WORKOUT LOGS / STATS
# ============================================================================

def get_my_workout_stats(db: Session, current_user: User) -> WorkoutUserStatsMessageResponse:
    stats = db.query(Workout_User_Stats).filter(Workout_User_Stats.trainee_id == current_user.id).first()
    if not stats:
        return WorkoutUserStatsMessageResponse(
            message="Workout stats do not exist yet or no workouts done yet.",
            trainee_id=current_user.id,  # type: ignore[arg-type]
            total_workouts_done=0,
            current_streak=0,
            longest_streak=0,
            total_minutes_trained=0,
            last_workout_log_id=None,
        )

    return WorkoutUserStatsMessageResponse(
        trainee_id=stats.trainee_id,  # type: ignore[arg-type]
        total_workouts_done=stats.total_workouts_done,  # type: ignore[arg-type]
        current_streak=stats.current_streak,  # type: ignore[arg-type]
        longest_streak=stats.longest_streak,  # type: ignore[arg-type]
        total_minutes_trained=stats.total_minutes_trained,  # type: ignore[arg-type]
        last_workout_log_id=stats.last_workout_log_id,  # type: ignore[arg-type]
    )


def finish_workout(
    db: Session,
    payload: FinishWorkoutLogCreate,
    current_user: User,
) -> FinishWorkoutLogResponse:
    if payload.plan_id is None:
        assignment = db.query(Workout_Plans_Users).filter(
            Workout_Plans_Users.trainee_id == current_user.id,
            Workout_Plans_Users.is_active == True,
        ).first()
        if not assignment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active workout plan found")
        plan_id = assignment.plan_id
    else:
        plan_id = payload.plan_id

    workout_link = db.query(Workouts_Workout_Plans).filter(
        Workouts_Workout_Plans.plan_id == plan_id,
        Workouts_Workout_Plans.workout_id == payload.workout_id,
    ).first()
    if not workout_link:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Workout is not part of the plan")

    duration_minutes = int((payload.end_datetime - payload.start_datetime).total_seconds() // 60)
    total_exercises_completed = db.query(Exercises_Workouts).filter(
        Exercises_Workouts.workout_id == payload.workout_id
    ).count()

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

    stats = db.query(Workout_User_Stats).filter(Workout_User_Stats.trainee_id == current_user.id).first()
    if not stats:
        stats = Workout_User_Stats(trainee_id=current_user.id)
        db.add(stats)
        db.flush()

    schedule_days = db.query(Workouts_Workout_Plans.day_of_week).filter(
        Workouts_Workout_Plans.plan_id == plan_id
    ).distinct().all()
    schedule_set = {row[0] for row in schedule_days if row[0] is not None}

    last_log = None
    if stats.last_workout_log_id is not None:
        last_log = db.query(Workout_Logs).filter(Workout_Logs.id == stats.last_workout_log_id).first()

    current_date = payload.start_datetime.date()

    if not last_log or not schedule_set:
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
            id=log.id,  # type: ignore[arg-type]
            trainee_id=log.trainee_id,  # type: ignore[arg-type]
            plan_id=log.plan_id,  # type: ignore[arg-type]
            workout_id=log.workout_id,  # type: ignore[arg-type]
            start_datetime=log.start_datetime,  # type: ignore[arg-type]
            end_datetime=log.end_datetime,  # type: ignore[arg-type]
            duration_minutes=log.duration_minutes,  # type: ignore[arg-type]
            total_exercises_completed=log.total_exercises_completed,  # type: ignore[arg-type]
        ),
        stats=WorkoutUserStatsResponse(
            trainee_id=stats.trainee_id,  # type: ignore[arg-type]
            total_workouts_done=stats.total_workouts_done,  # type: ignore[arg-type]
            current_streak=stats.current_streak,  # type: ignore[arg-type]
            longest_streak=stats.longest_streak,  # type: ignore[arg-type]
            total_minutes_trained=stats.total_minutes_trained,  # type: ignore[arg-type]
            last_workout_log_id=stats.last_workout_log_id,  # type: ignore[arg-type]
        ),
    )


# ============================================================================
# EXERCISE / PLAN TAGS
# ============================================================================

def list_exer_tags(db: Session, skip: int, limit: int) -> List[Exer_Tags]:
    return db.query(Exer_Tags).offset(skip).limit(limit).all()


def create_exer_tags(db: Session, tags: List[ExerTagCreate]) -> List[Exer_Tags]:
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


def get_exer_tag(db: Session, tag_id: int) -> Exer_Tags:
    tag = db.query(Exer_Tags).filter(Exer_Tags.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exercise tag not found")
    return tag


def delete_exer_tag(db: Session, tag_id: int, current_db_user: User) -> None:
    if current_db_user.role.value != "admin":  # type: ignore
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can delete exercise tags")

    tag = db.query(Exer_Tags).filter(Exer_Tags.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exercise tag not found")

    db.delete(tag)
    db.commit()


def list_plan_tags(db: Session, skip: int, limit: int) -> List[Plan_Tags]:
    return db.query(Plan_Tags).offset(skip).limit(limit).all()


def create_plan_tags(db: Session, tags: List[PlanTagCreate]) -> List[Plan_Tags]:
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


def get_plan_tag(db: Session, tag_id: int) -> Plan_Tags:
    tag = db.query(Plan_Tags).filter(Plan_Tags.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan tag not found")
    return tag


def delete_plan_tag(db: Session, tag_id: int, current_db_user: User) -> None:
    if current_db_user.role.value != "admin":  # type: ignore
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can delete plan tags")

    tag = db.query(Plan_Tags).filter(Plan_Tags.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan tag not found")

    db.delete(tag)
    db.commit()


def link_exercise_tag(db: Session, link: ExercisesExerTagsCreate) -> Any:
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


def link_workout_plan_tag(db: Session, link: WorkoutPlansPlanTagsCreate) -> Any:
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
