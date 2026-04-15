"""
Item models including Badges and Workout Schema
"""
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Boolean, BigInteger, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


class Badges(Base):
    """
    User Badges model
    """
    __tablename__ = "badges"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    icon_url = Column(String(512), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user_badges = relationship("User_Badges", back_populates="badge")

    def __repr__(self):
        return f"<Badges {self.title}>"
    

class User_Badges(Base):
    """
    Association table for User and Badges
    """
    __tablename__ = "user_badges"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)  # type: ignore
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)  # type: ignore
    badge_id = Column(UUID(as_uuid=True), ForeignKey("badges.id"), nullable=False)  # type: ignore

    # Timestamps
    awarded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="badges")
    badge = relationship("Badges", back_populates="user_badges")

    def __repr__(self):
        return f"<User_Badges user_id={self.user_id} badge_id={self.badge_id}>"


# ============================================================================
# WORKOUT SCHEMA MODELS
# ============================================================================

class Workout_Plans(Base):
    """
    Workout Plans model - Templates for workout programs
    """
    __tablename__ = "workout_plans"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    duration_minutes = Column(Integer, nullable=True)
    difficulty = Column(String, nullable=True)  # beginner/intermediate/advanced
    days_per_week = Column(Integer, nullable=True)
    ai_generated = Column(Boolean, default=False, nullable=False)
    is_trainer_provided = Column(Boolean, default=False, nullable=False)
    is_preset = Column(Boolean, default=False, server_default=text("false"), nullable=False)  # Indicates if this is a preset plan available to all users
    is_equipment_needed = Column(Boolean, default=False, server_default=text("false"), nullable=False)
    image_url = Column(Text, nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)  # This can be the id of the trainer, if created for a trainee, or the id of trainee if he created it for himself. It can be null if created by AI or imported from external source.
    
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    workout_plan_workouts = relationship("Workouts_Workout_Plans", back_populates="plan", cascade="all, delete-orphan")
    workout_plan_tags = relationship("Workout_Plans_Plan_Tags", back_populates="plan", cascade="all, delete-orphan")

    
    def __repr__(self):
        return f"<Workout_Plans {self.title}>"


class Workouts(Base):
    """
    Workouts model - Individual workout sessions
    """
    __tablename__ = "workouts"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    estimated_duration_minutes = Column(Integer, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    workout_plan_workouts = relationship("Workouts_Workout_Plans", back_populates="workout")
    workout_exercises = relationship("Exercises_Workouts", back_populates="workout", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Workouts {self.title}>"


class Exercises(Base):
    """
    Exercises model - Exercise library
    """
    __tablename__ = "exercises"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(Text, unique=True, nullable=False)
    description = Column(Text, nullable=True)
    instruction = Column(Text, nullable=True)
    is_equipment_needed = Column(Boolean, default=False, nullable=False)
    video_url = Column(Text, nullable=True)
    image_url = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    workout_exercises = relationship("Exercises_Workouts", back_populates="exercise")
    exercise_exer_tags = relationship("Exercises_Exer_Tags", back_populates="exercise", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Exercises {self.name}>"


class Workouts_Workout_Plans(Base):
    """
    Association table linking workout plans to workouts
    """
    __tablename__ = "workouts_workout_plans"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    plan_id = Column(BigInteger, ForeignKey("workout_plans.id", ondelete="CASCADE"), nullable=False)
    workout_id = Column(BigInteger, ForeignKey("workouts.id", ondelete="CASCADE"), nullable=False)
    order_index = Column(Integer, nullable=False)
    day_of_week = Column(Integer, nullable=False)  # 1=Monday, 2=Tuesday, etc.

    # Relationships
    plan = relationship("Workout_Plans", back_populates="workout_plan_workouts")
    workout = relationship("Workouts", back_populates="workout_plan_workouts")

    def __repr__(self):
        return f"<Workouts_Workout_Plans plan_id={self.plan_id} workout_id={self.workout_id}>"


class Exercises_Workouts(Base):
    """
    Association table linking workouts to exercises with sets/reps details
    """
    __tablename__ = "exercises_workouts"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    workout_id = Column(BigInteger, ForeignKey("workouts.id", ondelete="CASCADE"), nullable=False)
    exercise_id = Column(BigInteger, ForeignKey("exercises.id", ondelete="CASCADE"), nullable=False)
    sets = Column(Integer, nullable=True)
    reps = Column(Integer, nullable=True, default=0)
    is_by_reps = Column(Boolean, default=True)
    is_by_duration = Column(Boolean, default=False)
    duration_seconds = Column(Integer, nullable=True, default=0)
    rest_duration_seconds = Column(Integer, nullable=True, default=30)
    order_index = Column(Integer, nullable=True)

    # Relationships
    workout = relationship("Workouts", back_populates="workout_exercises")
    exercise = relationship("Exercises", back_populates="workout_exercises")

    def __repr__(self):
        return f"<Exercises_Workouts workout_id={self.workout_id} exercise_id={self.exercise_id}>"


class Plan_Tags(Base):
    """
    Tags model - Tags for categorizing workout plans
    """
    __tablename__ = "plan_tags"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(Text, unique=True, nullable=False)

    # Relationships
    workout_plan_tags = relationship("Workout_Plans_Plan_Tags", back_populates="tag", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Plan_Tags {self.name}>"


class Workout_Plans_Plan_Tags(Base):
    """
    Association table linking workout plans to tags
    """
    __tablename__ = "workout_plans_plan_tags"

    plan_id = Column(BigInteger, ForeignKey("workout_plans.id", ondelete="CASCADE"), primary_key=True)
    tag_id = Column(BigInteger, ForeignKey("plan_tags.id", ondelete="CASCADE"), primary_key=True)

    # Relationships
    plan = relationship("Workout_Plans", back_populates="workout_plan_tags")
    tag = relationship("Plan_Tags", back_populates="workout_plan_tags")

    def __repr__(self):
        return f"<Workout_Plans_Plan_Tags plan_id={self.plan_id} tag_id={self.tag_id}>"


class Exer_Tags(Base):
    """
    Tags model - Tags for categorizing exercises
    """
    __tablename__ = "exer_tags"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(Text, unique=True, nullable=False)

    # Relationships
    exercise_exer_tags = relationship("Exercises_Exer_Tags", back_populates="tag", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Exer_Tags {self.name}>"


class Exercises_Exer_Tags(Base):
    """
    Association table linking exercises to tags
    """
    __tablename__ = "exercises_exer_tags"

    exercise_id = Column(BigInteger, ForeignKey("exercises.id", ondelete="CASCADE"), primary_key=True)
    tag_id = Column(BigInteger, ForeignKey("exer_tags.id", ondelete="CASCADE"), primary_key=True)

    # Relationships
    exercise = relationship("Exercises", back_populates="exercise_exer_tags")
    tag = relationship("Exer_Tags", back_populates="exercise_exer_tags")

    def __repr__(self):
        return f"<Exercises_Exer_Tags exercise_id={self.exercise_id} tag_id={self.tag_id}>"





