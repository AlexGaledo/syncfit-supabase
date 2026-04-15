"""Unit tests for authentication endpoints."""
from conftest import JWT_PAYLOAD


def test_get_me(client):
    # response_model=UserProfileBase strips sub/email/role; just verify 200
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 200
    assert isinstance(response.json(), dict)


def test_verify_token(client):
    response = client.post("/api/v1/auth/verify")
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True
    assert data["user_id"] == JWT_PAYLOAD["sub"]
    assert data["email"] == JWT_PAYLOAD["email"]


def test_get_me_unauthorized(raw_client):
    # No Authorization header → HTTPBearer raises 4xx
    response = raw_client.get("/api/v1/auth/me")
    assert response.status_code in (401, 403)
