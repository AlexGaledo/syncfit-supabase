"""
Pydantic schemas package
"""
from app.schemas.user import (
    UserRole, UserType, UserGender,
    UserBase, UserCreate, UserUpdate, UserResponse, OAuthUser,
    UserProfileBase, UserProfileCreate, UserProfileUpdate, UserProfileResponse,
    UserSupplementBase, UserSupplementCreate, UserSupplementResponse,
    UserLimitationBase, UserLimitationCreate, UserLimitationResponse,
    WeightLossProgressBase, WeightLossProgressCreate, WeightLossProgressResponse,
    EventLogBase, EventLogCreate, EventLogResponse,
    SupabaseTokenProfile,
)
from app.schemas.item import (
    BadgeBase, BadgeCreate, BadgeUpdate, BadgeResponse,
    UserBadgeCreate, UserBadgeResponse,
    WorkoutPlanBase, WorkoutPlanCreate, WorkoutPlanUpdate, WorkoutPlanResponse,
    WorkoutBase, WorkoutCreate, WorkoutUpdate, WorkoutResponse,
    ExerciseBase, ExerciseCreate, ExerciseUpdate, ExerciseResponse,
    WorkoutsWorkoutPlansBase, WorkoutsWorkoutPlansCreate, WorkoutsWorkoutPlansResponse,
    ExercisesWorkoutsBase, ExercisesWorkoutsCreate, ExercisesWorkoutsUpdate, ExercisesWorkoutsResponse,
    PlanTagBase, PlanTagCreate, PlanTagResponse,
    ExerTagBase, ExerTagCreate, ExerTagResponse,
    WorkoutPlansPlanTagsCreate, WorkoutPlansPlanTagsResponse,
    ExercisesExerTagsCreate, ExercisesExerTagsResponse,
)
from app.schemas.meal_plan import (
    MealCategory, MealType,
    MealBase, MealCreate, MealUpdate, MealResponse,
    MealPlanBase, MealPlanCreate, MealPlanUpdate, MealPlanResponse, MealPlanDetailResponse,
    MealPlanItemBase, MealPlanItemCreate, MealPlanItemUpdate, MealPlanItemResponse,
    NutritionSummary,
)
from app.schemas.social import (
    ConnectionStatus, ConversationType, ConversationRole, MessageType,
    ConnectionBase, ConnectionCreate, ConnectionUpdate, ConnectionResponse,
    ConversationBase, ConversationCreate, ConversationResponse,
    ConversationParticipantBase, ConversationParticipantCreate, ConversationParticipantResponse,
    MessageBase, MessageCreate, MessageResponse,
)
