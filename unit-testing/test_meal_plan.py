"""Unit tests for meal plan endpoints."""
from datetime import date, datetime
from types import SimpleNamespace
from uuid import uuid4

from conftest import SUPABASE_ID, USER_ID


def _fake_meal():
    return SimpleNamespace(
        id=uuid4(),
        name="Chicken Rice",
        description=None,
        category="lunch",
        calories=400,
        protein_grams=30.0,
        carbs_grams=50.0,
        fat_grams=10.0,
        fiber_grams=2.0,
        serving_size="1 plate",  # MealResponse.serving_size is Optional[str]
        image_url=None,
        is_custom=True,
        created_by=USER_ID,
        created_at=datetime(2024, 1, 1),
        updated_at=None,
    )


def _fake_plan():
    return SimpleNamespace(
        id=uuid4(),
        user_id=USER_ID,
        date=date(2024, 1, 15),
        notes=None,
        target_calories=2000,
        created_at=datetime(2024, 1, 1),
        updated_at=None,
        items=[],
    )


# ---------------------------------------------------------------------------
# Meals (food library)
# ---------------------------------------------------------------------------

def test_get_meals_empty(client, mock_db):
    mock_db.query.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []
    response = client.get("/api/v1/meal-plans/meals")
    assert response.status_code == 200
    assert response.json() == []


def test_get_meal_by_id(client, mock_db):
    # _visible_meals_query chains query().filter().filter().first()
    mock_db.query.return_value.filter.return_value.filter.return_value.first.return_value = _fake_meal()
    meal_id = uuid4()
    response = client.get(f"/api/v1/meal-plans/meals/{meal_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Chicken Rice"


def test_get_meal_not_found(client, mock_db):
    # conftest defaults double-filter chain to None → triggers 404
    response = client.get(f"/api/v1/meal-plans/meals/{uuid4()}")
    assert response.status_code == 404


def test_create_meal(client, mock_db):
    def refresh_mock(obj):
        obj.id = uuid4()
        obj.created_at = datetime(2024, 1, 1)
        obj.is_custom = True
        obj.created_by = USER_ID

    mock_db.refresh.side_effect = refresh_mock

    payload = {"name": "Oatmeal", "calories": 300, "serving_size": "1 bowl"}
    response = client.post("/api/v1/meal-plans/meals", json=payload)
    assert response.status_code == 201


def test_delete_meal_not_found(client, mock_db):
    mock_db.query.return_value.filter.return_value.first.return_value = None
    response = client.delete(f"/api/v1/meal-plans/meals/{uuid4()}")
    assert response.status_code == 404


def test_delete_meal_forbidden(client, mock_db):
    # delete_meal queries Meals directly (single filter), not _visible_meals_query
    other_meal = _fake_meal()
    other_meal.created_by = uuid4()  # different owner → 403
    mock_db.query.return_value.filter.return_value.first.return_value = other_meal
    response = client.delete(f"/api/v1/meal-plans/meals/{other_meal.id}")
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Meal Plans (daily plans)
# ---------------------------------------------------------------------------

def test_get_my_meal_plans_empty(client, mock_db):
    mock_db.query.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []
    response = client.get("/api/v1/meal-plans/")
    assert response.status_code == 200
    assert response.json() == []


def test_create_meal_plan(client, mock_db):
    """Test creating a new daily meal plan."""
    response = client.post(
        "/api/v1/meal-plans/",
        json={"date": "2024-01-15", "target_calories": 2200},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["target_calories"] == 2200
    assert "id" in data


def test_create_meal_plan_conflict(client, mock_db):
    # Plan already exists for this date → 400
    mock_db.query.return_value.filter.return_value.first.return_value = _fake_plan()
    payload = {"date": "2024-01-15"}
    response = client.post("/api/v1/meal-plans/", json=payload)
    assert response.status_code == 400


def test_get_meal_plan_by_date(client, mock_db):
    """Test retrieving an existing meal plan by its date."""
    # The endpoint chains two filters: filter(user_id).filter(date)
    mock_db.query.return_value.options.return_value.filter.return_value.first.return_value = (
        _fake_plan()
    )
    response = client.get("/api/v1/meal-plans/date/2024-01-15")
    assert response.status_code == 200
    data = response.json()
    assert data["target_calories"] == 2000


def test_get_meal_plan_not_found(client, mock_db):
    """Test that a 404 is returned for a non-existent meal plan."""
    # The default mock_db fixture already returns None for queries
    response = client.get("/api/v1/meal-plans/by-date/2025-11-20")
    assert response.status_code == 404


def test_delete_meal_plan_not_found(client, mock_db):
    mock_db.query.return_value.filter.return_value.first.return_value = None
    response = client.delete(f"/api/v1/meal-plans/{uuid4()}")
    assert response.status_code == 404


def test_get_meal_plan_by_date_not_found(client, mock_db):
    mock_db.query.return_value.options.return_value.filter.return_value.first.return_value = None
    response = client.get("/api/v1/meal-plans/date/2024-01-01")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Nutrition summary
# ---------------------------------------------------------------------------

def test_nutrition_summary_not_found(client, mock_db):
    mock_db.query.return_value.options.return_value.filter.return_value.first.return_value = None
    response = client.get(f"/api/v1/meal-plans/{uuid4()}/nutrition")
    assert response.status_code == 404
