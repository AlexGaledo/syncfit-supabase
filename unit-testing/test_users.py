"""Unit tests for user endpoints."""
from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

from conftest import SUPABASE_ID, USER_ID, fake_db_user
from app.models.user import UserGender, UserRole, UserType


def _fake_user():
    return fake_db_user()


# ---------------------------------------------------------------------------
# GET /users/{user_id}
# ---------------------------------------------------------------------------

def test_get_user(client, mock_db):
    mock_db.query.return_value.filter.return_value.first.return_value = _fake_user()
    response = client.get(f"/api/v1/users/{USER_ID}")
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert str(data["id"]) == str(USER_ID)


def test_get_user_not_found(client, mock_db):
    mock_db.query.return_value.filter.return_value.first.return_value = None
    response = client.get(f"/api/v1/users/{uuid4()}")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# POST /users/
# ---------------------------------------------------------------------------

def test_create_user_new(client, mock_db):
    # No existing user → create a new one
    from app.models.user import UserRole, UserType, UserGender

    mock_db.query.return_value.filter.return_value.first.return_value = None

    def refresh_mock(obj):
        # Set all fields required by UserResponse
        obj.id = USER_ID
        obj.created_at = datetime(2024, 1, 1)
        obj.supabase_user_id = SUPABASE_ID
        obj.role = UserRole.user
        obj.type = UserType.trainee
        obj.gender = UserGender.others
        obj.email_verified = False
        obj.is_active = True

    mock_db.refresh.side_effect = refresh_mock

    response = client.post("/api/v1/users/")
    assert response.status_code == 201


def test_create_user_existing(client, mock_db):
    # Existing user → return it (idempotent)
    mock_db.query.return_value.filter.return_value.first.return_value = _fake_user()
    response = client.post("/api/v1/users/")
    # Returns existing user with 201 (the endpoint always returns 201 status)
    assert response.status_code == 201
    assert response.json()["email"] == "test@example.com"


# ---------------------------------------------------------------------------
# PATCH /users/{user_id}
# ---------------------------------------------------------------------------

def test_update_user(client, mock_db):
    # Both filter calls (get user + get caller) return same fake user (owner)
    mock_db.query.return_value.filter.return_value.first.return_value = _fake_user()
    response = client.patch(f"/api/v1/users/{USER_ID}", json={"full_name": "Updated"})
    assert response.status_code == 200


def test_update_user_not_found(client, mock_db):
    mock_db.query.return_value.filter.return_value.first.return_value = None
    response = client.patch(f"/api/v1/users/{uuid4()}", json={"full_name": "X"})
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /users/{user_id}
# ---------------------------------------------------------------------------

def test_delete_user(client, mock_db):
    mock_db.query.return_value.filter.return_value.first.return_value = _fake_user()
    response = client.delete(f"/api/v1/users/{USER_ID}")
    assert response.status_code == 204


# ---------------------------------------------------------------------------
# GET /users/get_users  (admin only)
# ---------------------------------------------------------------------------

def test_get_all_users_forbidden_for_regular_user(client, mock_db):
    # fake_db_user has role=UserRole.user, not admin → 403
    mock_db.query.return_value.filter.return_value.first.return_value = _fake_user()
    response = client.get("/api/v1/users/get_users")
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# GET /users/{user_id}/badges
# ---------------------------------------------------------------------------

def test_get_user_badges_empty(client, mock_db):
    mock_db.query.return_value.filter.return_value.first.return_value = _fake_user()
    mock_db.query.return_value.filter.return_value.all.return_value = []
    response = client.get(f"/api/v1/users/{USER_ID}/badges")
    assert response.status_code == 200
    assert response.json() == []
