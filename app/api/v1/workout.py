"""Workout API endpoints - Ford"""
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Union
from uuid import UUID

from app.database import get_db
from app.dependencies import get_current_user, get_current_db_user
from app.models.user import User
from app.models.item import DifficultyLevel
from app.schemas.item import (
    ExerciseCreate, ExerciseUpdate, ExerciseResponse,
    WorkoutUpdate, WorkoutResponse,
    WorkoutPlanUpdate, WorkoutPlanResponse,
    WorkoutPlansUsersCreate, WorkoutPlansUsersResponse, WorkoutPlansUsersUpdate,
    SeederFullWorkoutPlan, CreateFullWorkoutPlan,
    CreateFullWorkoutRequest, UpdateFullWorkout,
    FullWorkoutPlanDetailResponse, FullWorkoutDetail,
    FinishWorkoutLogCreate, FinishWorkoutLogResponse,
    WorkoutUserStatsMessageResponse,
    ExerTagCreate, ExerTagResponse,
    PlanTagCreate, PlanTagResponse,
    ExercisesExerTagsCreate, ExercisesExerTagsResponse,
    WorkoutPlansPlanTagsCreate, WorkoutPlansPlanTagsResponse, AIGenerateRequest,
)
from app.schemas.user import UserInfoContextResponse
from app.services import workout_service, ai_service

workout_router = APIRouter(prefix="/workout", tags=["Workout"])


@workout_router.get("/user-info-context", response_model=UserInfoContextResponse)
def get_user_info_context(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_db_user),
):
    """
    Retrieve specific contextual information about the user.
    Includes gender, age (calculated from birthdate), weight, and height.
    """
    return workout_service.get_user_info_context(db, current_user)


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
    current_user: dict = Depends(get_current_user),
):
    """
    Retrieve all exercises with optional filtering by name, equipment needs, and tags.
    """
    return workout_service.list_exercises(db, name, is_equipment_needed, exer_tags, skip, limit)


@workout_router.get("/exercises/{exercise_id}", response_model=ExerciseResponse)
def get_exercise(
    exercise_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Retrieve a single exercise with its tags."""
    return workout_service.get_exercise(db, exercise_id)


@workout_router.post("/exercises", response_model=List[ExerciseResponse], status_code=status.HTTP_201_CREATED)
def create_exercises(
    exercises: List[ExerciseCreate],
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Create one or more new exercises. If an exercise with the same name already exists, reuse it instead of creating a duplicate.
    This is for admin purposes only. Ordinary users should not be creating exercises - they should use the existing library when building workouts.
    """
    return workout_service.create_exercises(db, exercises)


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
    return workout_service.update_exercise(db, exercise_id, exercise_data, current_db_user)


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
    workout_service.delete_exercise(db, exercise_id, current_db_user)
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
    return workout_service.list_workouts(db, skip, limit)


@workout_router.post("/workouts/full", response_model=FullWorkoutDetail, status_code=status.HTTP_201_CREATED)
def create_full_workout(
    workout_data: CreateFullWorkoutRequest,
    db: Session = Depends(get_db),
    current_db_user: User = Depends(get_current_db_user),
):
    """
    Creates a new workout, links it to a workout plan, and inserts its exercises.
    """
    return workout_service.create_full_workout(db, workout_data, current_db_user)


@workout_router.get("/workouts/{workout_id}", response_model=WorkoutResponse)
def get_workout(
    workout_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Retrieve a single workout by ID."""
    return workout_service.get_workout(db, workout_id)


@workout_router.get("/workouts/{workout_id}/full", response_model=FullWorkoutDetail)
def get_full_workout(
    workout_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Retrieve all details of a single workout, including all details of its associated exercises."""
    return workout_service.get_full_workout(db, workout_id)


@workout_router.patch("/workouts/{workout_id}", response_model=WorkoutResponse)
def update_workout(
    workout_id: int,
    workout_data: WorkoutUpdate,
    db: Session = Depends(get_db),
    current_db_user: User = Depends(get_current_db_user),
):
    """Update a workout metadata."""
    return workout_service.update_workout(db, workout_id, workout_data)


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
    return workout_service.update_full_workout(db, workout_id, workout_data)


@workout_router.delete("/workouts/{workout_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workout(
    workout_id: int,
    db: Session = Depends(get_db),
    current_db_user: User = Depends(get_current_db_user),
):
    """Delete a workout and all its exercise links."""
    workout_service.delete_workout(db, workout_id)
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
    current_user: dict = Depends(get_current_user),
):
    """
    Search and filter workout plans. Returns workout plan information, including tags.
    """
    return workout_service.list_workout_plans(
        db, title, difficulty, days_per_week, is_preset, is_equipment_needed, plan_tags, skip, limit
    )


# ============================================================================
# WORKOUT STATS AND LOGS
# ============================================================================

@workout_router.get("/stats/my-stats", response_model=WorkoutUserStatsMessageResponse)
def get_my_workout_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_db_user),
):
    """
    Retrieve the current user's workout stats.
    If none exist, return default values and a message.
    """
    return workout_service.get_my_workout_stats(db, current_user)


@workout_router.post("/logs/finish-workout", response_model=FinishWorkoutLogResponse, status_code=status.HTTP_201_CREATED)
def finish_workout(
    payload: FinishWorkoutLogCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_db_user),
):
    """
    Log a completed workout session and update the user's workout stats.
    """
    return workout_service.finish_workout(db, payload, current_user)


@workout_router.get("/workout-plans/{plan_id}/full", response_model=FullWorkoutPlanDetailResponse)
def get_full_workout_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Retrieve all details of a workout plan, including its associated workouts and their exercises.
    """
    return workout_service.get_full_workout_plan(db, plan_id)


@workout_router.get("/workout-plans/my-schedule")
def get_workout_plan_schedule(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_db_user),
):
    """
    Retrieve the workout schedule for the user's active plan.
    It includes which workouts are scheduled for which days of the week, and which of those workouts have been completed in the current week based on workout logs.
    """
    return workout_service.get_my_schedule(db, current_user)


@workout_router.get("/workout-plans/today-workout")
def get_today_workout(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_db_user),
):
    """
    Retrieve today's workout session for the user's active plan, or the most recent pending workout.
    """
    return workout_service.get_today_workout(db, current_user)


@workout_router.get("/workout-plans/my-workout-plan", response_model=Union[List[FullWorkoutPlanDetailResponse], FullWorkoutPlanDetailResponse])
def get_my_workout_plan(
    all: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_db_user),
):
    """
    Retrieve workout plans assigned to the current user (where the user is trainee).
    Returned object can be the active workout plan or the list of all workout plans assigned to the user (active + inactive) based on the query parameter.

    ### Query Parameters:
    - **all** (bool, optional):
        - `false` (Default): Returns only the **currently active** workout plan object.
        - `true`: Returns a **list** of all assigned workout plans (Active + Inactive).

    """
    return workout_service.get_my_workout_plan(db, current_user, all)


@workout_router.get("/workout-plans/created-by/{user_id}", response_model=List[WorkoutPlanResponse])
def get_workout_plans_created_by_user(
    user_id: UUID,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Retrieve all workout plans metadata created by a specific user.
    This is to view all plans created by a specific user.
    """
    return workout_service.list_plans_created_by_user(db, user_id, skip, limit)


@workout_router.post("/workout-plans/create-full", response_model=FullWorkoutPlanDetailResponse, status_code=status.HTTP_201_CREATED)
def create_full_workout_plan(
    plan_data: CreateFullWorkoutPlan,
    db: Session = Depends(get_db),
    current_db_user: User = Depends(get_current_db_user),
):
    """
    Creates a complete workout plan including workouts and their associations with existing exercises.
    This endpoint is intended for end users (trainees/trainers) to construct a program using the existing exercise library.
    All operations are performed in a single transaction.
    This does not assign the plan to any user - it only creates the plan and its related workouts. Use the /assign-workout-plan endpoint to link it to a trainee/trainer.
    """
    return workout_service.create_full_workout_plan(db, plan_data, current_db_user)


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
    return workout_service.update_workout_plan(db, plan_id, plan_data, current_db_user)


@workout_router.delete("/workout-plans/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workout_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    current_db_user: User = Depends(get_current_db_user),
):
    """
    Delete a workout plan and associated workouts. Only the creator or an admin may do this.
    """
    workout_service.delete_workout_plan(db, plan_id, current_db_user)
    return None


@workout_router.post("/workout-plans/ai-generate-full", status_code=status.HTTP_200_OK)
def ai_generate_full_workout_plan(
    request: AIGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_db_user),
):
    """
    Generate a full workout plan using the Gemini API based on user context and prompt.
    Returns JSON matching the CreateFullWorkoutPlan schema.
    This only returns the JSON data. To save it to the database, use the /workout-plans/create-full endpoint with the returned JSON as the payload. To assign the generated plan to a user, use the /workout-plans/assign endpoint with the created plan ID and user ID.
    """
    user_context = workout_service.get_user_info_context(db, current_user)
    return ai_service.generate_workout_plan(request, user_context)


@workout_router.post("/workout-plans/seed-full", status_code=status.HTTP_201_CREATED)
def seed_full_workout_plan(
    plan_data: SeederFullWorkoutPlan,
    db: Session = Depends(get_db),
    current_db_user: User = Depends(get_current_db_user),
):
    """
    Seeds a complete workout plan, including exercises, workouts, and their associations.
    This is a generic seeder that accepts a JSON payload with the full plan structure.
    All operations are performed in a single transaction.
    This is for admin use only.
    """
    return workout_service.seed_full_workout_plan(db, plan_data, current_db_user)


# ============================================================================
# WORKOUT PLANS TO USERS ASSIGNMENTS  — LIST / GET / CREATE / UPDATE / DELETE
# ============================================================================

@workout_router.get("/workout-plans/assign", response_model=List[WorkoutPlansUsersResponse])
def get_all_workout_plan_assignments(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_db_user),
):
    """
    Retrieve all workout plan user assignments. (Admin only)
    """
    return workout_service.list_assignments(db, skip, limit, current_user)


@workout_router.get("/workout-plans/assign/{assignment_id}", response_model=WorkoutPlansUsersResponse)
def get_workout_plan_assignment(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_db_user),
):
    """
    Retrieve a single workout plan user assignment.
    """
    return workout_service.get_assignment(db, assignment_id, current_user)


@workout_router.post("/workout-plans/assign", response_model=WorkoutPlansUsersResponse, status_code=status.HTTP_201_CREATED)
def assign_workout_plan_to_user(
    assignment: WorkoutPlansUsersCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_db_user),
):
    """
    Assign a workout plan to a trainee, and optionally a trainer.
    Ensures that only one workout plan can be active for a trainee at any time.
    """
    return workout_service.assign_workout_plan(db, assignment, current_user)


@workout_router.patch("/workout-plans/assign/{assignment_id}", response_model=WorkoutPlansUsersResponse)
def update_workout_plan_assignment(
    assignment_id: int,
    assignment_update: WorkoutPlansUsersUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_db_user),
):
    """
    Update a workout plan user assignment.
    """
    return workout_service.update_assignment(db, assignment_id, assignment_update, current_user)


@workout_router.delete("/workout-plans/assign/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workout_plan_assignment(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_db_user),
):
    """
    Delete a workout plan user assignment.
    """
    workout_service.delete_assignment(db, assignment_id, current_user)
    return None


# ============================================================================
# EXERCISE AND WORKOUT PLAN TAGS — LIST / GET / CREATE / DELETE
# ============================================================================


@workout_router.get("/exer-tags", response_model=List[ExerTagResponse])
def get_all_exer_tags(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Retrieve all exercise tags.
    """
    return workout_service.list_exer_tags(db, skip, limit)


@workout_router.post("/exer-tags", response_model=List[ExerTagResponse], status_code=status.HTTP_201_CREATED)
def create_exer_tags(
    tags: List[ExerTagCreate],
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Create multiple exercise tags using a list of tag names. See exer_tags.json for sample input.
    """
    return workout_service.create_exer_tags(db, tags)


@workout_router.get("/exer-tags/{tag_id}", response_model=ExerTagResponse)
def get_exer_tag(
    tag_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Retrieve a single exercise tag."""
    return workout_service.get_exer_tag(db, tag_id)


@workout_router.delete("/exer-tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_exer_tag(
    tag_id: int,
    db: Session = Depends(get_db),
    current_db_user: User = Depends(get_current_db_user),
):
    """Delete an exercise tag. (Admin only)"""
    workout_service.delete_exer_tag(db, tag_id, current_db_user)
    return None


@workout_router.get("/plan-tags", response_model=List[PlanTagResponse])
def get_all_plan_tags(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Retrieve all plan tags.
    """
    return workout_service.list_plan_tags(db, skip, limit)


@workout_router.post("/plan-tags", response_model=List[PlanTagResponse], status_code=status.HTTP_201_CREATED)
def create_plan_tags(
    tags: List[PlanTagCreate],
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Create multiple plan tags using a list of tag names. See plan_tags.json for sample input.
    """
    return workout_service.create_plan_tags(db, tags)


@workout_router.get("/plan-tags/{tag_id}", response_model=PlanTagResponse)
def get_plan_tag(
    tag_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Retrieve a single plan tag."""
    return workout_service.get_plan_tag(db, tag_id)


@workout_router.delete("/plan-tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_plan_tag(
    tag_id: int,
    db: Session = Depends(get_db),
    current_db_user: User = Depends(get_current_db_user),
):
    """Delete a plan tag. (Admin only)"""
    workout_service.delete_plan_tag(db, tag_id, current_db_user)
    return None


@workout_router.post("/exer-tags/link-to-exercise", response_model=ExercisesExerTagsResponse, status_code=status.HTTP_201_CREATED)
def create_exercise_tag_link(
    link: ExercisesExerTagsCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Link a tag to an exercise using tag_id and exercise_id
    """
    return workout_service.link_exercise_tag(db, link)


@workout_router.post("/plan-tags/link-to-workout-plan", response_model=WorkoutPlansPlanTagsResponse, status_code=status.HTTP_201_CREATED)
def create_workout_plan_tag_link(
    link: WorkoutPlansPlanTagsCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Link a tag to a workout plan using tag_id and plan_id
    """
    return workout_service.link_workout_plan_tag(db, link)
