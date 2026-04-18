"""Unit tests for meal plan endpoints."""
from datetime import date, datetime
from types import SimpleNamespace
from uuid import uuid4

from app.models.meal_plan import Meals, Meal_Plans, Meal_Plan_Items
from conftest import SUPABASE_ID, USER_ID


def _fake_meal(**kwargs):
    defaults = {
        "id": uuid4(),
        "name": "Chicken Rice",
        "description": None,
        "category": "lunch",
        "calories": 400,
        "protein_grams": 30.0,
        "carbs_grams": 50.0,
        "fat_grams": 10.0,
        "fiber_grams": 2.0,
        "serving_size": "1 plate",
        "image_url": None,
        "is_custom": True,
        "created_by": USER_ID,
        "created_at": datetime(2024, 1, 1),
        "updated_at": None,
    }
    return Meals(**{**defaults, **kwargs})


def _fake_plan(**kwargs):
    defaults = {
        "id": uuid4(),
        "user_id": USER_ID,
        "date": date(2024, 1, 15),
        "notes": None,
        "target_calories": 2000,
        "created_at": datetime(2024, 1, 1),
        "updated_at": None,
        "items": [],
    }
    return Meal_Plans(**{**defaults, **kwargs})


def _fake_item(plan_id, meal, **kwargs):
    defaults = {
        "id": uuid4(),
        "meal_plan_id": plan_id,
        "meal_id": meal.id,
        "meal": meal,
        "meal_type": "lunch",
        "servings": 1.0,
        "created_at": datetime(2024, 1, 1),
    }
    return Meal_Plan_Items(**{**defaults, **kwargs})


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


def test_nutrition_summary_calculates_correctly(client, mock_db):
    """Verify that the nutrition summary correctly sums up all meal items."""
    plan = _fake_plan()
    meal1 = _fake_meal(
        name="Breakfast Burrito",
        calories=400,
        protein_grams=25,
        carbs_grams=30,
        fat_grams=20,
        fiber_grams=5,
    )
    meal2 = _fake_meal(
        name="Protein Shake",
        calories=300,
        protein_grams=40,
        carbs_grams=10,
        fat_grams=10,
        fiber_grams=2,
    )

    plan.items = [
        _fake_item(plan.id, meal1, servings=1.0),
        _fake_item(plan.id, meal2, servings=1.5),
    ]

    # get_nutrition_summary uses the get_meal_plan_for_user dependency
    mock_db.query.return_value.options.return_value.filter.return_value.first.return_value = plan

    response = client.get(f"/api/v1/meal-plans/{plan.id}/nutrition")
    assert response.status_code == 200
    summary = response.json()

    # Expected: (400 * 1.0) + (300 * 1.5) = 400 + 450 = 850
    assert summary["total_calories"] == 850
    # Expected: (25 * 1.0) + (40 * 1.5) = 25 + 60 = 85
    assert summary["total_protein_grams"] == 85
    # Expected: (30 * 1.0) + (10 * 1.5) = 30 + 15 = 45
    assert summary["total_carbs_grams"] == 45
    # Expected: (20 * 1.0) + (10 * 1.5) = 20 + 15 = 35
    assert summary["total_fat_grams"] == 35
    # Expected: (5 * 1.0) + (2 * 1.5) = 5 + 3 = 8
    assert summary["total_fiber_grams"] == 8
    assert summary["target_calories"] == 2000
    assert summary["remaining_calories"] == 1150  # 2000 - 850


# ---------------------------------------------------------------------------
# Meal Plan Items
# ---------------------------------------------------------------------------

def test_add_meal_to_plan(client, mock_db):
    """Test adding a new meal item to an existing plan."""
    plan = _fake_plan()
    meal = _fake_meal()

    # The endpoint uses a complex query with an outerjoin
    mock_db.query.return_value.outerjoin.return_value.filter.return_value.first.return_value = (plan, meal)

    def refresh_mock(obj):
        obj.id = uuid4()
        obj.meal = meal  # Attach the meal for the response

    mock_db.refresh.side_effect = refresh_mock
    # The final query to eager-load the meal for the response
    item = _fake_item(plan.id, meal)
    mock_db.query.return_value.options.return_value.filter.return_value.first.return_value = item


    payload = {
        "meal_id": str(meal.id),
        "meal_type": "breakfast",
        "servings": 1.0,
    }
    response = client.post(f"/api/v1/meal-plans/{plan.id}/items", json=payload)
    assert response.status_code == 201
    assert response.json()["meal"]["name"] == "Chicken Rice"


def test_add_meal_to_plan_meal_not_found(client, mock_db):
    plan = _fake_plan()
    # When the meal is not found, the joined query returns (plan, None)
    mock_db.query.return_value.outerjoin.return_value.filter.return_value.first.return_value = (plan, None)

    payload = {"meal_id": str(uuid4()), "meal_type": "lunch", "servings": 1}
    response = client.post(f"/api/v1/meal-plans/{plan.id}/items", json=payload)
    assert response.status_code == 404
    assert "Meal not found" in response.json()["detail"]


def test_update_meal_plan_item(client, mock_db):
    """Test updating an item's servings or meal type."""
    plan = _fake_plan()
    meal = _fake_meal()
    item = _fake_item(plan.id, meal, servings=1.0)

    # Mock the two queries in the endpoint
    mock_db.query.return_value.filter.return_value.first.side_effect = [plan, item]

    def refresh_mock(obj):
        obj.servings = 1.5

    mock_db.refresh.side_effect = refresh_mock
    # Mock the final query for the response
    item.servings = 1.5
    mock_db.query.return_value.options.return_value.filter.return_value.first.return_value = item

    response = client.patch(
        f"/api/v1/meal-plans/{plan.id}/items/{item.id}",
        json={"servings": 1.5},
    )
    assert response.status_code == 200


def test_update_meal_plan_item_not_found(client, mock_db):
    plan = _fake_plan()
    # First query for the plan succeeds, second for the item fails
    mock_db.query.return_value.filter.return_value.first.side_effect = [plan, None]

    response = client.patch(
        f"/api/v1/meal-plans/{plan.id}/items/{uuid4()}",
        json={"servings": 2.0},
    )
    assert response.status_code == 404
    assert "Meal plan item not found" in response.json()["detail"]


def test_delete_meal_plan_item(client, mock_db):
    """Test successfully removing a meal from a plan."""
    plan = _fake_plan()
    item = SimpleNamespace(id=uuid4(), meal_plan_id=plan.id)
    # Mock the two queries in the endpoint
    mock_db.query.return_value.filter.return_value.first.side_effect = [plan, item]

    response = client.delete(f"/api/v1/meal-plans/{plan.id}/items/{item.id}")
    assert response.status_code == 204


def test_delete_meal_plan_item_not_found(client, mock_db):
    plan = _fake_plan()
    # First query for the plan succeeds, second for the item fails
    mock_db.query.return_value.filter.return_value.first.side_effect = [plan, None]

    response = client.delete(f"/api/v1/meal-plans/{plan.id}/items/{uuid4()}")
    assert response.status_code == 404
    assert "Meal plan item not found" in response.json()["detail"]


def test_get_meal_plan_by_id_unauthorized(client, mock_db):
    """A user cannot fetch another user's plan by its ID."""
    # The get_meal_plan_for_user dependency returns None, triggering a 404
    mock_db.query.return_value.options.return_value.filter.return_value.first.return_value = None
    response = client.get(f"/api/v1/meal-plans/{uuid4()}")
    assert response.status_code == 404


def test_update_meal_plan_item_unauthorized(client, mock_db):
    """A user cannot update an item in a plan they don't own."""
    # The first query for the plan fails, returning None
    mock_db.query.return_value.filter.return_value.first.return_value = None
    response = client.patch(
        f"/api/v1/meal-plans/{uuid4()}/items/{uuid4()}",
        json={"servings": 1.0},
    )
    assert response.status_code == 404
    assert "Meal plan not found" in response.json()["detail"]


def test_delete_meal_plan_item_unauthorized(client, mock_db):
    """A user cannot delete an item from a plan they don't own."""
    # The first query for the plan fails, returning None
    mock_db.query.return_value.filter.return_value.first.return_value = None
    response = client.delete(f"/api/v1/meal-plans/{uuid4()}/items/{uuid4()}")
    assert response.status_code == 404
    assert "Meal plan not found" in response.json()["detail"]


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def test_create_meal_with_negative_values(client, mock_db):
    """Test that creating a meal with negative nutritional values fails."""
    payload = {
        "name": "Negative Food",
        "calories": -100,
        "protein_grams": -10,
        "carbs_grams": 5,
        "fat_grams": -5,
        "serving_size": "1 unit",
    }
    response = client.post("/api/v1/meal-plans/meals", json=payload)
    assert response.status_code == 422  # Unprocessable Entity
    errors = response.json()["detail"]
    assert any("Input should be greater than or equal to 0" in e["msg"] for e in errors if e["loc"] == ["body", "calories"])
    assert any("Input should be greater than or equal to 0" in e["msg"] for e in errors if e["loc"] == ["body", "protein_grams"])
    assert any("Input should be greater than or equal to 0" in e["msg"] for e in errors if e["loc"] == ["body", "fat_grams"])


def test_update_meal_plan_with_negative_calories(client, mock_db):
    """Test that updating a plan with negative target calories fails."""
    plan = _fake_plan()
    mock_db.query.return_value.options.return_value.filter.return_value.first.return_value = plan

    response = client.patch(
        f"/api/v1/meal-plans/{plan.id}",
        json={"target_calories": -500},
    )
    assert response.status_code == 422
    errors = response.json()["detail"]
    assert any("Input should be greater than or equal to 0" in e["msg"] for e in errors if e["loc"] == ["body", "target_calories"])
