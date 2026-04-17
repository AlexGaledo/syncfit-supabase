"""
User database model
"""
from sqlalchemy import Column, String, DateTime, Boolean, Enum, ForeignKey, Integer, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
import enum
from app.database import Base


class UserRole(enum.Enum):
    """Enum for user roles"""
    admin = 'admin'
    user = 'user'


class UserType(enum.Enum):
    """Enum for user types"""
    trainer = 'internal'
    trainee = 'external'


class UserGender(enum.Enum):
    """Enum for user gender"""
    male = 'male'
    female = 'female'
    others = 'others'


class User(Base):
    """
    User model - synced with Supabase Auth
    """
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)  # type: ignore
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=True)
    role = Column(Enum(UserRole), default=UserRole.user, nullable=False)  # type: ignore    
    type = Column(Enum(UserType), default=UserType.trainee, nullable=False)  # type: ignore
    gender = Column(Enum(UserGender), default=UserGender.others, nullable=False)  # type: ignore
    birthdate = Column(DateTime, nullable=True)
    email_verified = Column(Boolean, default=False, nullable=False)

    # Supabase user ID (from auth.users)
    supabase_user_id = Column(UUID(as_uuid=True), unique=True, index=True, nullable=False)  # type: ignore
    is_active = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    profile = relationship("User_Profile", uselist=False, back_populates="user", cascade="all, delete-orphan")
    badges = relationship("User_Badges", back_populates="user")
    weight_progress = relationship("Weight_Loss_Progress", backref="user", cascade="all, delete-orphan")
    event_logs = relationship("Event_Logs", backref="user", cascade="all, delete-orphan")
    meal_plans = relationship("Meal_Plans", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.email}>"


class User_Profile(Base):
    """
    User Profile model
    """
    __tablename__ = "user_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)  # type: ignore
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True)  # type: ignore
    address = Column(String, nullable=True)
    phone_number = Column(String, nullable=True)
    bio = Column(String, nullable=True)
    calorie_goal_daily = Column(Integer, nullable=True)
    sleep_quality = Column(String, nullable=True)  # sleep goal poor fair good
    weight = Column(Integer, nullable=True)  # weight in kg
    height = Column(Integer, nullable=True)  # height in cm

    user = relationship("User", back_populates="profile") 
    supplements = relationship("User_Supplements", back_populates="user", cascade="all, delete-orphan")
    limitations = relationship("User_Limitations", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User_Profile {self.user_id}>"
    

class User_Supplements(Base):
    """
    User Supplements model
    """
    __tablename__ = "user_supplements"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)  # type: ignore
    user_id = Column(UUID(as_uuid=True), ForeignKey("user_profiles.id"), nullable=False)  # type: ignore
    supplement_name = Column(String, nullable=False)
    user = relationship("User_Profile", back_populates="supplements")

    def __repr__(self):
        return f"<User_Supplements {self.user_id} - {self.supplement_name}>"
    

class User_Limitations(Base):
    """
    User Limitations model
    """
    __tablename__ = "user_limitations"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)  # type: ignore
    user_id = Column(UUID(as_uuid=True), ForeignKey("user_profiles.id"), nullable=False)  # type: ignore
    limitation_description = Column(String, nullable=False)
    user = relationship("User_Profile", back_populates="limitations")

    def __repr__(self):
        return f"<User_Limitations {self.user_id} - {self.limitation_description}>"
    

class Weight_Loss_Progress(Base): #tbf
    """
    Weight Loss Progress model
    """
    __tablename__ = "weight_loss_progress"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)  # type: ignore
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)  # type: ignore
    date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    weight = Column(Integer, nullable=False)  # weight in kg
    base_weight = Column(Integer, nullable=True)  # base weight in kg for progress tracking

    def __repr__(self):
        return f"<Weight_Loss_Progress {self.user_id} - {self.date} - {self.weight}>"
    

class Event_Logs(Base):
    """
    Event Logs model
    """
    __tablename__ = "event_logs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)  # type: ignore
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)  # type: ignore
    event_type = Column(String, nullable=False)
    event_timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    event_details = Column(JSON, nullable=True)

    def __repr__(self):
        return f"<Event_Logs {self.user_id} - {self.event_type} - {self.event_timestamp}>"



