"""Workout API endpoints - Ford"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.dependencies import get_current_user
from app.models.item import Exercises
from app.schemas.item import ExerciseCreate, ExerciseResponse

workout_router = APIRouter(prefix="/workout", tags=["Workout"])


@workout_router.post("/exercises", response_model=List[ExerciseResponse], status_code=status.HTTP_201_CREATED)
def create_exercises(
    exercises: List[ExerciseCreate],
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Create one or more new exercises.
    """
    created_exercises = []
    for exercise_data in exercises:
        db_exercise = Exercises(**exercise_data.model_dump())
        db.add(db_exercise)
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
    return exercises



