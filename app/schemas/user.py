"""
User schemas for request/response validation
"""
from pydantic import BaseModel, EmailStr, ConfigDict, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from enum import Enum


# ============================================================================
# ENUMS
# ============================================================================

class UserRole(str, Enum):
    admin = "admin"
    user = "user"

class UserType(str, Enum):
    trainer = "trainer"
    trainee = "trainee"

class UserGender(str, Enum):
    male = "male"
    female = "female"
    others = "others"


class OnboardingRole(str, Enum):
    trainee = "trainee"
    trainer = "trainer"


class OnboardingGoal(str, Enum):
    lose_weight = "lose_weight"
    ai_coach = "ai_coach"
    bulk = "bulk"
    endurance = "endurance"
    trying = "trying"
    others = "others"


class OnboardingGender(str, Enum):
    male = "male"
    female = "female"


class OnboardingAthleticism(str, Enum):
    no_experience = "no_experience"
    some_experience = "some_experience"
    somewhat_athletic = "somewhat_athletic"
    very_athletic = "very_athletic"
    professional = "professional"


class OnboardingDietPreference(str, Enum):
    vegetarian = "vegetarian"
    vegan = "vegan"
    omnivore = "omnivore"
    pescatarian = "pescatarian"
    flexitarian = "flexitarian"
    none = "none"


class OnboardingDaysCommitment(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    daily = "daily"


class OnboardingExercisePreference(str, Enum):
    weightlifting = "weightlifting"
    calisthenics = "calisthenics"
    powerlifting = "powerlifting"
    hiit = "hiit"
    yoga = "yoga"
    crossfit = "crossfit"
    general = "general"
    sports = "sports"
    none = "none"


class OnboardingSleepValue(str, Enum):
    insomniac = "insomniac"
    bad = "bad"
    normal = "normal"
    great = "great"
    excellent = "excellent"


class OnboardingEquipment(str, Enum):
    commercial = "commercial"
    home_gym = "home_gym"
    dumbbells = "dumbbells"
    bands = "bands"
    bodyweight = "bodyweight"
    outdoor = "outdoor"


class OnboardingLearningPreference(str, Enum):
    visual = "visual"
    auditory = "auditory"
    read_write = "read/write"
    kinesthetic = "kinesthetic"
    interactive = "interactive"


class OnboardingWeightUnit(str, Enum):
    kg = "kg"
    lbs = "lbs"


class OnboardingHeightUnit(str, Enum):
    cm = "cm"
    inch = "inch"


class OnboardingCalorieUnit(str, Enum):
    kcal = "kcal"
    joules = "joules"


# ============================================================================
# USER SCHEMAS
# ============================================================================

class UserBase(BaseModel):
    """Base user schema"""
    email: EmailStr
    full_name: Optional[str] = None
    role: UserRole = UserRole.user
    type: UserType = UserType.trainee
    gender: UserGender = UserGender.others
    birthdate: Optional[datetime] = None
    email_verified: bool = False


class UserCreate(UserBase):
    """Schema for creating a user"""
    supabase_user_id: UUID


class UserCreateRequest(BaseModel):
    """
    Body accepted by POST /users/.
    email and supabase_user_id are sourced from the verified JWT token,
    so callers only need to supply optional profile fields.
    """
    full_name: Optional[str] = None
    role: UserRole = UserRole.user
    type: UserType = UserType.trainee
    gender: UserGender = UserGender.others
    birthdate: Optional[datetime] = None


class UserUpdate(BaseModel):
    """Schema for updating a user"""
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    type: Optional[UserType] = None
    gender: Optional[UserGender] = None
    birthdate: Optional[datetime] = None
    email_verified: Optional[bool] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    """Schema for user response"""
    id: UUID
    supabase_user_id: UUID
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class UserListItem(BaseModel):
    """Minimal user listing response"""
    id: UUID
    full_name: Optional[str] = None
    email: EmailStr

    model_config = ConfigDict(from_attributes=True)


class OAuthUser(BaseModel):
    """Schema for user created via OAuth"""
    email: EmailStr
    user_id: str  # Supabase user ID
    oauth_provider: str  # e.g., 'google', 'github'
    oauth_token: str


# ============================================================================
# USER PROFILE SCHEMAS
# ============================================================================

class UserProfileBase(BaseModel):
    """Base user profile schema"""
    address: Optional[str] = None
    phone_number: Optional[str] = None
    bio: Optional[str] = None
    calorie_goal_daily: Optional[int] = Field(default=None, ge=0)
    macro_protein_pct: Optional[int] = Field(default=None, ge=0, le=100)
    macro_carb_pct: Optional[int] = Field(default=None, ge=0, le=100)
    macro_fat_pct: Optional[int] = Field(default=None, ge=0, le=100)
    sleep_quality: Optional[str] = None
    weight: Optional[float] = None
    height: Optional[float] = None


class UserProfileCreate(UserProfileBase):
    """Schema for creating a user profile"""
    user_id: UUID


class UserProfileUpdate(UserProfileBase):
    """Schema for updating a user profile"""
    pass


class UserProfileResponse(UserProfileBase):
    """Schema for user profile response"""
    id: UUID
    user_id: UUID

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# USER SUPPLEMENTS SCHEMAS
# ============================================================================

class UserSupplementBase(BaseModel):
    """Base supplement schema"""
    supplement_name: str


class UserSupplementCreate(UserSupplementBase):
    """Schema for creating a supplement"""
    user_id: UUID


class UserSupplementResponse(UserSupplementBase):
    """Schema for supplement response"""
    id: UUID
    user_id: UUID

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# USER LIMITATIONS SCHEMAS
# ============================================================================

class UserLimitationBase(BaseModel):
    """Base limitation schema"""
    limitation_description: str


class UserLimitationCreate(UserLimitationBase):
    """Schema for creating a limitation"""
    user_id: UUID


class UserLimitationResponse(UserLimitationBase):
    """Schema for limitation response"""
    id: UUID
    user_id: UUID

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# WEIGHT LOSS PROGRESS SCHEMAS
# ============================================================================

class WeightLossProgressBase(BaseModel):
    """Base weight loss progress schema"""
    weight: float  # kg


class WeightLossProgressCreate(WeightLossProgressBase):
    """Schema for creating a weight loss progress entry"""
    user_id: UUID


class WeightLossProgressResponse(WeightLossProgressBase):
    """Schema for weight loss progress response"""
    id: UUID
    user_id: UUID
    date: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# EVENT LOGS SCHEMAS
# ============================================================================

class EventLogBase(BaseModel):
    """Base event log schema"""
    event_type: str
    event_details: Optional[dict] = None


class EventLogCreate(EventLogBase):
    """Schema for creating an event log"""
    user_id: UUID


class EventLogResponse(EventLogBase):
    """Schema for event log response"""
    id: UUID
    user_id: UUID
    event_timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# SUPABASE TOKEN PROFILE
# ============================================================================

class SupabaseTokenProfile(BaseModel):
    """Schema for user profile extracted from Supabase JWT token"""
    sub: str  # User ID from Supabase
    email: str
    role: Optional[str] = None


class UserInfoContextResponse(BaseModel):
    """Schema for user information context response"""
    user_id: UUID
    gender: Optional[str] = None
    age: Optional[int] = None
    weight: Optional[float] = None
    height: Optional[float] = None


# ============================================================================
# USER ONBOARDING SCHEMAS
# ============================================================================

class UserOnboardingBase(BaseModel):
    """Base user onboarding schema"""
    model_config = ConfigDict(populate_by_name=True)

    role: Optional[OnboardingRole] = None
    goal: Optional[OnboardingGoal] = None
    gender: Optional[OnboardingGender] = None
    age: Optional[int] = None
    weight: Optional[float] = None
    weight_unit: Optional[OnboardingWeightUnit] = Field(default=None, validation_alias="weightUnit", serialization_alias="weightUnit")
    height: Optional[float] = None
    height_unit: Optional[OnboardingHeightUnit] = Field(default=None, validation_alias="heightUnit", serialization_alias="heightUnit")
    athleticism: Optional[OnboardingAthleticism] = None
    physical_limitations: Optional[List[str]] = Field(default=None, validation_alias="physicalLimitations", serialization_alias="physicalLimitations")
    diet_preference: Optional[OnboardingDietPreference] = Field(default=None, validation_alias="dietPreference", serialization_alias="dietPreference")
    days_commitment: Optional[OnboardingDaysCommitment] = Field(default=None, validation_alias="daysCommitment", serialization_alias="daysCommitment")
    fitness_experience: Optional[str] = Field(default=None, validation_alias="fitnessExperience", serialization_alias="fitnessExperience")
    exercise_preference: Optional[OnboardingExercisePreference] = Field(default=None, validation_alias="exercisePreference", serialization_alias="exercisePreference")
    taking_supplements: Optional[bool] = Field(default=None, validation_alias="takingSupplements", serialization_alias="takingSupplements")
    supplements_used: Optional[List[str]] = Field(default=None, validation_alias="supplementsUsed", serialization_alias="supplementsUsed")
    calorie_intake: Optional[int] = Field(default=None, validation_alias="calorieIntake", serialization_alias="calorieIntake")
    macro_protein_pct: Optional[int] = Field(default=None, ge=0, le=100, validation_alias="macroProteinPct", serialization_alias="macroProteinPct")
    macro_carb_pct: Optional[int] = Field(default=None, ge=0, le=100, validation_alias="macroCarbPct", serialization_alias="macroCarbPct")
    macro_fat_pct: Optional[int] = Field(default=None, ge=0, le=100, validation_alias="macroFatPct", serialization_alias="macroFatPct")
    calorie_unit: Optional[OnboardingCalorieUnit] = Field(default=None, validation_alias="calorieUnit", serialization_alias="calorieUnit")
    sleep_value: Optional[OnboardingSleepValue] = Field(default=None, validation_alias="sleepValue", serialization_alias="sleepValue")
    equipment_available: Optional[OnboardingEquipment] = Field(default=None, validation_alias="equipmentAvailable", serialization_alias="equipmentAvailable")
    learning_preference: Optional[OnboardingLearningPreference] = Field(default=None, validation_alias="learningPreference", serialization_alias="learningPreference")


class UserOnboardingCreate(UserOnboardingBase):
    """Schema for creating user onboarding"""
    user_id: UUID


class UserOnboardingUpdate(UserOnboardingBase):
    """Schema for updating user onboarding"""
    pass


class UserOnboardingResponse(UserOnboardingBase):
    """Schema for user onboarding response"""
    id: UUID
    user_id: UUID

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
