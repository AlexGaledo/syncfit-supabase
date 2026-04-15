"""Unit tests for workout endpoints."""
from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4


def _fake_exercise():
    return SimpleNamespace(
        id=1,
        name="Push Up",
        description="A classic push up",
        instruction="Keep body straight",
        is_equipment_needed=False,
        video_url=None,
        image_url=None,
        created_at=datetime(2024, 1, 1),
        exercise_exer_tags=[],
    )


def _fake_workout():
    return SimpleNamespace(
        id=1,
        title="Morning Workout",
        description=None,
        estimated_duration_minutes=30,
        created_at=datetime(2024, 1, 1),
        updated_at=None,
    )


def _fake_plan():
    return SimpleNamespace(
        id=1,
        title="Beginner Plan",
        description=None,
        duration_minutes=60,
        difficulty=None,
        days_per_week=3,
        ai_generated=False,
        is_trainer_provided=False,
        assigned_to=None,
        created_by=None,
        created_at=datetime(2024, 1, 1),
        updated_at=None,
        workout_plan_tags=[],
    )


# ---------------------------------------------------------------------------
# Exercises
# ---------------------------------------------------------------------------

def test_get_all_exercises_empty(client, mock_db):
    mock_db.query.return_value.offset.return_value.limit.return_value.all.return_value = []
    response = client.get("/api/v1/workout/exercises")
    assert response.status_code == 200
    assert response.json() == []


def test_get_exercise_by_id(client, mock_db):
    mock_db.query.return_value.filter.return_value.first.return_value = _fake_exercise()
    response = client.get("/api/v1/workout/exercises/1")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Push Up"
    assert data["tags"] == []


def test_get_exercise_not_found(client, mock_db):
    mock_db.query.return_value.filter.return_value.first.return_value = None
    response = client.get("/api/v1/workout/exercises/999")
    assert response.status_code == 404


def test_create_exercises(client, mock_db):
    # Exercise with same name doesn't exist → create new
    mock_db.query.return_value.filter.return_value.first.return_value = None

    def refresh_mock(obj):
        obj.id = 1
        obj.created_at = datetime(2024, 1, 1)
        obj.exercise_exer_tags = []

    mock_db.refresh.side_effect = refresh_mock

    payload = [{"name": "Squat", "is_equipment_needed": False}]
    response = client.post("/api/v1/workout/exercises", json=payload)
    assert response.status_code == 201


# ---------------------------------------------------------------------------
# Workouts
# ---------------------------------------------------------------------------

def test_get_all_workouts_empty(client, mock_db):
    mock_db.query.return_value.offset.return_value.limit.return_value.all.return_value = []
    response = client.get("/api/v1/workout/workouts")
    assert response.status_code == 200
    assert response.json() == []


def test_get_workout_by_id(client, mock_db):
    mock_db.query.return_value.filter.return_value.first.return_value = _fake_workout()
    response = client.get("/api/v1/workout/workouts/1")
    assert response.status_code == 200
    assert response.json()["title"] == "Morning Workout"


def test_get_workout_not_found(client, mock_db):
    mock_db.query.return_value.filter.return_value.first.return_value = None
    response = client.get("/api/v1/workout/workouts/999")
    assert response.status_code == 404


def test_create_workout(client, mock_db):
    def refresh_mock(obj):
        obj.id = 1
        obj.created_at = datetime(2024, 1, 1)

    mock_db.refresh.side_effect = refresh_mock

    response = client.post("/api/v1/workout/workouts", json={"title": "New Workout"})
    assert response.status_code == 201
    assert response.json()["title"] == "New Workout"


# ---------------------------------------------------------------------------
# Workout Plans
# ---------------------------------------------------------------------------

def test_get_workout_plans_empty(client, mock_db):
    mock_db.query.return_value.offset.return_value.limit.return_value.all.return_value = []
    # filter chain for optional filters
    mock_db.query.return_value.filter.return_value.offset.return_value.limit.return_value.all.return_value = []
    response = client.get("/api/v1/workout/workout-plans")
    assert response.status_code == 200


def test_create_workout_plan(client, mock_db):
    def refresh_mock(obj):
        obj.id = 1
        obj.created_at = datetime(2024, 1, 1)

    mock_db.refresh.side_effect = refresh_mock

    payload = {"title": "My Plan", "ai_generated": False, "is_trainer_provided": False}
    response = client.post("/api/v1/workout/workout-plans", json=payload)
    assert response.status_code == 201
    assert response.json()["title"] == "My Plan"


def test_get_full_workout_plan_not_found(client, mock_db):
    mock_db.query.return_value.filter.return_value.first.return_value = None
    response = client.get("/api/v1/workout/workout-plans/999/full")
    assert response.status_code == 404


def test_delete_workout_plan_not_found(client, mock_db):
    mock_db.query.return_value.filter.return_value.first.return_value = None
    response = client.delete("/api/v1/workout/workout-plans/999")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Tags
# ---------------------------------------------------------------------------

def test_get_exer_tags_empty(client, mock_db):
    mock_db.query.return_value.offset.return_value.limit.return_value.all.return_value = []
    response = client.get("/api/v1/workout/exer-tags")
    assert response.status_code == 200
    assert response.json() == []


def test_get_plan_tags_empty(client, mock_db):
    mock_db.query.return_value.offset.return_value.limit.return_value.all.return_value = []
    response = client.get("/api/v1/workout/plan-tags")
    assert response.status_code == 200
    assert response.json() == []
