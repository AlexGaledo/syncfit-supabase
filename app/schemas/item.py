"""
Item & Workout schemas for request/response validation
"""
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from enum import Enum


class DifficultyLevel(str, Enum):
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"


# ============================================================================
# BADGES SCHEMAS
# ============================================================================

class BadgeBase(BaseModel):
    """Base badge schema"""
    title: str
    description: Optional[str] = None
    icon_url: Optional[str] = None


class BadgeCreate(BadgeBase):
    """Schema for creating a badge"""
    pass


class BadgeUpdate(BaseModel):
    """Schema for updating a badge"""
    title: Optional[str] = None
    description: Optional[str] = None
    icon_url: Optional[str] = None


class BadgeResponse(BadgeBase):
    """Schema for badge response"""
    id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# USER BADGES SCHEMAS
# ============================================================================

class UserBadgeCreate(BaseModel):
    """Schema for awarding a badge to a user"""
    user_id: UUID
    badge_id: UUID


class UserBadgeResponse(BaseModel):
    """Schema for user badge response"""
    id: UUID
    user_id: UUID
    badge_id: UUID
    awarded_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# WORKOUT PLANS SCHEMAS
# ============================================================================

class WorkoutPlanBase(BaseModel):
    """Base workout plan schema"""
    title: str
    description: Optional[str] = None
    duration_minutes: Optional[int] = None
    difficulty: Optional[DifficultyLevel] = None
    days_per_week: Optional[int] = None
    ai_generated: bool = False
    is_preset: bool = False
    is_equipment_needed: bool = False
    image_url: Optional[str] = None


class WorkoutPlanCreate(WorkoutPlanBase):
    """Schema for creating a workout plan"""
    created_by: Optional[UUID] = None


class WorkoutPlanUpdate(BaseModel):
    """Schema for updating a workout plan"""
    title: Optional[str] = None
    description: Optional[str] = None
    duration_minutes: Optional[int] = None
    difficulty: Optional[DifficultyLevel] = None
    days_per_week: Optional[int] = None
    ai_generated: Optional[bool] = None
    is_preset: Optional[bool] = None
    is_equipment_needed: Optional[bool] = None
    image_url: Optional[str] = None


class WorkoutPlanResponse(WorkoutPlanBase):
    """Schema for workout plan response"""
    id: int
    created_by: Optional[UUID] = None
    tags: List[str] = []
    created_at: datetime
    updated_at: Optional[datetime] = None


    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# WORKOUTS SCHEMAS
# ============================================================================

class WorkoutBase(BaseModel):
    """Base workout schema"""
    title: str
    description: Optional[str] = None
    estimated_duration_minutes: Optional[int] = None


class WorkoutCreate(WorkoutBase):
    """Schema for creating a workout"""
    pass


class WorkoutUpdate(BaseModel):
    """Schema for updating a workout"""
    title: Optional[str] = None
    description: Optional[str] = None
    estimated_duration_minutes: Optional[int] = None


class WorkoutResponse(WorkoutBase):
    """Schema for workout response"""
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# EXERCISES SCHEMAS
# ============================================================================

class ExerciseBase(BaseModel):
    """Base exercise schema"""
    name: str
    description: Optional[str] = None
    instruction: Optional[str] = None
    is_equipment_needed: bool = False
    video_url: Optional[str] = None
    image_url: Optional[str] = None
    is_by_reps: bool = True
    is_by_duration: bool = False
    tags: Optional[List[str]] = None


class ExerciseCreate(ExerciseBase):
    """Schema for creating an exercise"""
    pass


class ExerciseUpdate(BaseModel):
    """Schema for updating an exercise"""
    name: Optional[str] = None
    description: Optional[str] = None
    instruction: Optional[str] = None
    is_equipment_needed: Optional[bool] = None
    video_url: Optional[str] = None
    image_url: Optional[str] = None
    is_by_reps: Optional[bool] = None
    is_by_duration: Optional[bool] = None


class ExerciseResponse(ExerciseBase):
    """Schema for exercise response"""
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# WORKOUTS_WORKOUT_PLANS SCHEMAS
# ============================================================================

class WorkoutsWorkoutPlansBase(BaseModel):
    """Base schema for linking a workout to a plan"""
    plan_id: int
    workout_id: int
    order_index: int
    day_of_week: int # Monday = 1, Sunday = 7


class WorkoutsWorkoutPlansCreate(WorkoutsWorkoutPlansBase):
    """Schema for adding a workout to a plan"""
    pass


class WorkoutsWorkoutPlansResponse(WorkoutsWorkoutPlansBase):
    """Schema for workout plan workout response"""
    id: int

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# EXERCISES_WORKOUTS SCHEMAS
# ============================================================================

class ExercisesWorkoutsBase(BaseModel):
    """Base schema for linking an exercise to a workout"""
    workout_id: int
    exercise_id: int
    sets: Optional[int] = None
    reps: Optional[int] = None
    duration_seconds: Optional[int] = 0
    rest_duration_seconds: Optional[int] = 30
    order_index: Optional[int] = None


class ExercisesWorkoutsCreate(ExercisesWorkoutsBase):
    """Schema for adding an exercise to a workout"""
    pass


class ExercisesWorkoutsUpdate(BaseModel):
    """Schema for updating a workout exercise"""
    sets: Optional[int] = None
    reps: Optional[int] = None
    duration_seconds: Optional[int] = None
    rest_duration_seconds: Optional[int] = None
    order_index: Optional[int] = None


class ExercisesWorkoutsResponse(ExercisesWorkoutsBase):
    """Schema for workout exercise response"""
    id: int

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# PLAN_TAGS SCHEMAS
# ============================================================================

class PlanTagBase(BaseModel):
    """Base plan tag schema"""
    name: str


class PlanTagCreate(PlanTagBase):
    """Schema for creating a plan tag"""
    pass


class PlanTagResponse(PlanTagBase):
    """Schema for plan tag response"""
    id: int

    model_config = ConfigDict(from_attributes=True)

# ============================================================================
# EXER_TAGS SCHEMAS
# ============================================================================

class ExerTagBase(BaseModel):
    """Base exer tag schema"""
    name: str

class ExerTagCreate(ExerTagBase):
    """Schema for creating an exer tag"""
    pass

class ExerTagResponse(ExerTagBase):
    """Schema for exer tag response"""
    id: int

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# WORKOUT_PLANS_PLAN_TAGS SCHEMAS
# ============================================================================

class WorkoutPlansPlanTagsCreate(BaseModel):
    """Schema for adding a tag to a workout plan"""
    plan_id: int
    tag_id: int


class WorkoutPlansPlanTagsResponse(WorkoutPlansPlanTagsCreate):
    """Schema for workout plan tag response"""

    model_config = ConfigDict(from_attributes=True)

# ============================================================================
# EXERCISES_EXER_TAGS SCHEMAS
# ============================================================================

class ExercisesExerTagsCreate(BaseModel):
    """Schema for adding a tag to an exercise"""
    exercise_id: int
    tag_id: int

class ExercisesExerTagsResponse(ExercisesExerTagsCreate):
    """Schema for exercise tag response"""

    model_config = ConfigDict(from_attributes=True)

# ============================================================================
# SEEDER SCHEMAS
# ============================================================================

class SeederExerciseWorkout(BaseModel):
    exercise_name: str
    sets: Optional[int] = None
    reps: Optional[int] = None
    duration_seconds: Optional[int] = 0
    rest_duration_seconds: Optional[int] = 30
    order_index: int

class SeederWorkout(BaseModel):
    title: str
    description: Optional[str] = None
    estimated_duration_minutes: Optional[int] = None
    exercises: List[SeederExerciseWorkout]
    order_index: int
    day_of_week: int # Monday = 1, Sunday = 7

class SeederWorkoutPlan(BaseModel):
    title: str
    description: Optional[str] = None
    difficulty: Optional[DifficultyLevel] = None
    days_per_week: Optional[int] = None
    ai_generated: bool = False
    is_preset: bool = False
    is_equipment_needed: bool = False
    image_url: Optional[str] = None
    created_by: Optional[UUID] = None
    duration_minutes: Optional[int] = None
    workouts: List[SeederWorkout]
    tags: Optional[List[str]] = None

class SeederFullWorkoutPlan(BaseModel):
    plan: SeederWorkoutPlan
    exercises: List[ExerciseCreate]

# ============================================================================
# USER FULL PLAN CREATION SCHEMAS
# ============================================================================

class CreateExerciseWorkout(BaseModel):
    exercise_id: int
    sets: Optional[int] = None
    reps: Optional[int] = None
    duration_seconds: Optional[int] = 0
    rest_duration_seconds: Optional[int] = 30
    order_index: int

class CreateWorkout(BaseModel):
    title: str
    description: Optional[str] = None
    estimated_duration_minutes: Optional[int] = None
    exercises: List[CreateExerciseWorkout]
    order_index: int 
    day_of_week: int # Monday = 1, Sunday = 7

class CreateFullWorkoutRequest(CreateWorkout):
    plan_id: int

class CreateFullWorkoutPlan(BaseModel):
    title: str
    description: Optional[str] = None
    difficulty: Optional[DifficultyLevel] = None
    days_per_week: Optional[int] = None
    ai_generated: bool = False
    is_preset: bool = False
    is_equipment_needed: bool = False
    image_url: Optional[str] = None
    duration_minutes: Optional[int] = None
    workouts: List[CreateWorkout]
    tags: Optional[List[str]] = None

class AIGenerateRequest(BaseModel):
    prompt: str

# ============================================================================
# USER FULL PLAN UPDATE SCHEMAS
# ============================================================================

class UpdateFullWorkoutExercise(BaseModel):
    exercise_id: int
    sets: Optional[int] = None
    reps: Optional[int] = None
    duration_seconds: Optional[int] = None
    rest_duration_seconds: Optional[int] = None
    order_index: int

class UpdateFullWorkout(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    estimated_duration_minutes: Optional[int] = None
    exercises: Optional[List[UpdateFullWorkoutExercise]] = None

# ============================================================================
# FULL DETAIL RESPONSES
# ============================================================================

class FullExerciseDetail(BaseModel):
    exercise_id: int
    name: str
    description: Optional[str] = None
    instruction: Optional[str] = None
    is_equipment_needed: bool
    video_url: Optional[str] = None
    image_url: Optional[str] = None
    tags: List[str] = []
    sets: Optional[int] = None
    reps: Optional[int] = None
    is_by_reps: bool
    is_by_duration: bool
    duration_seconds: Optional[int] = None
    rest_duration_seconds: Optional[int] = None
    order_index: Optional[int] = None

class FullWorkoutDetail(BaseModel):
    workout_id: int
    title: str
    description: Optional[str] = None
    estimated_duration_minutes: Optional[int] = None
    day_of_week: Optional[int] = None # Monday = 1, Sunday = 7
    order_index: Optional[int] = None
    exercises: List[FullExerciseDetail] = []

class FullWorkoutPlanDetailResponse(BaseModel):
    plan_id: int
    title: str
    description: Optional[str] = None
    duration_minutes: Optional[int] = None
    difficulty: Optional[DifficultyLevel] = None
    days_per_week: Optional[int] = None
    ai_generated: bool
    is_preset: bool
    is_equipment_needed: bool
    image_url: Optional[str] = None
    created_by: Optional[UUID] = None
    tags: List[str] = []
    workouts: List[FullWorkoutDetail] = []
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# WORKOUT_PLANS_USERS SCHEMAS
# ============================================================================

class WorkoutPlansUsersBase(BaseModel):
    """Base schema for assigning a workout plan to a user"""
    trainee_id: UUID
    trainer_id: Optional[UUID] = None
    plan_id: int
    is_trainer_provided: bool = False
    is_active: bool = True
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None



class WorkoutPlansUsersCreate(WorkoutPlansUsersBase):
    """Schema for assigning a workout plan to a user"""
    pass


class WorkoutPlansUsersUpdate(BaseModel):
    """Schema for updating a workout plan assignment"""
    is_active: Optional[bool] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class WorkoutPlansUsersResponse(WorkoutPlansUsersBase):
    """Schema for workout plan user response"""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# WORKOUT LOGS SCHEMAS
# ============================================================================

class WorkoutLogBase(BaseModel):
    """Base workout log schema"""
    trainee_id: UUID
    plan_id: Optional[int] = None
    workout_id: Optional[int] = None
    start_datetime: datetime
    end_datetime: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    total_exercises_completed: Optional[int] = None


class WorkoutLogCreate(WorkoutLogBase):
    """Schema for creating a workout log"""
    pass


class FinishWorkoutLogCreate(BaseModel):
    """Schema for finishing a workout session and logging it"""
    plan_id: Optional[int] = None
    workout_id: int
    start_datetime: datetime
    end_datetime: datetime


class WorkoutLogUpdate(BaseModel):
    """Schema for updating a workout log"""
    end_datetime: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    total_exercises_completed: Optional[int] = None


class WorkoutLogResponse(WorkoutLogBase):
    """Schema for workout log response"""
    id: int

    model_config = ConfigDict(from_attributes=True)


class FinishWorkoutLogResponse(BaseModel):
    """Schema for finish workout response"""
    message: str
    workout_log: WorkoutLogResponse
    stats: "WorkoutUserStatsResponse"


# ============================================================================
# WORKOUT USER STATS SCHEMAS
# ============================================================================

class WorkoutUserStatsBase(BaseModel):
    """Base workout user stats schema"""
    trainee_id: UUID
    total_workouts_done: int = 0
    current_streak: int = 0
    longest_streak: int = 0
    total_minutes_trained: int = 0
    last_workout_log_id: Optional[int] = None


class WorkoutUserStatsCreate(WorkoutUserStatsBase):
    """Schema for creating workout user stats"""
    pass


class WorkoutUserStatsUpdate(BaseModel):
    """Schema for updating workout user stats"""
    total_workouts_done: Optional[int] = None
    current_streak: Optional[int] = None
    longest_streak: Optional[int] = None
    total_minutes_trained: Optional[int] = None
    last_workout_log_id: Optional[int] = None


class WorkoutUserStatsResponse(WorkoutUserStatsBase):
    """Schema for workout user stats response"""
    model_config = ConfigDict(from_attributes=True)


class WorkoutUserStatsMessageResponse(WorkoutUserStatsResponse):
    """Schema for workout user stats response with optional message"""
    message: Optional[str] = None
