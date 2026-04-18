"""
User schemas for request/response validation
"""
from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional
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
    calorie_goal_daily: Optional[int] = None
    sleep_quality: Optional[str] = None  # poor/fair/good
    weight: Optional[float] = None  # kg
    height: Optional[float] = None  # cm


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
