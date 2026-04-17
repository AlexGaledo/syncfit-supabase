"""
Shared test fixtures and setup for all unit tests.
Mocks DB session and auth dependencies so tests run without a real database.
"""
import os
import sys

# Ensure the project root is on sys.path so `app` can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set fake env vars BEFORE importing any app modules (avoids engine init errors)
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg2://fake:fake@localhost/fakedb")
os.environ.setdefault("SUPABASE_URL", "https://fake.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "fakekey")
os.environ.setdefault("SUPABASE_JWT_SECRET", "fakesecret")

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app import create_app
from app.dependencies import get_current_db_user, get_current_user, get_db
from app.models.user import UserGender, UserRole, UserType

# ---------------------------------------------------------------------------
# Shared fake data
# ---------------------------------------------------------------------------

USER_ID = uuid4()
SUPABASE_ID = uuid4()
OTHER_USER_ID = uuid4()

JWT_PAYLOAD = {"sub": str(SUPABASE_ID), "email": "test@example.com", "role": "user"}


def fake_db_user():
    """A SimpleNamespace that looks like a User ORM object."""
    return SimpleNamespace(
        id=USER_ID,
        email="test@example.com",
        full_name="Test User",
        role=UserRole.user,
        type=UserType.trainee,
        gender=UserGender.others,
        birthdate=None,
        email_verified=False,
        supabase_user_id=SUPABASE_ID,
        is_active=True,
        created_at=datetime(2024, 1, 1),
        updated_at=None,
        profile=None,
        badges=[],
    )


# ---------------------------------------------------------------------------
# refresh side-effect: sets DB-generated fields so Pydantic validation passes
# ---------------------------------------------------------------------------

def _refresh_handler(obj):
    """
    Mimics what db.refresh() does: sets id, created_at, and any column defaults
    on newly-created ORM objects so Pydantic response validation passes.
    """
    import sqlalchemy

    if not hasattr(obj, "__mapper__"):
        return

    id_col = obj.__mapper__.columns.get("id")
    if id_col is not None and getattr(obj, "id", None) is None:
        obj.id = 1 if isinstance(id_col.type, sqlalchemy.Integer) else uuid4()

    if getattr(obj, "created_at", None) is None:
        obj.created_at = datetime(2024, 1, 1)

    # Apply SQLAlchemy column-level Python defaults for any still-None fields
    for col_name, col in obj.__mapper__.columns.items():
        if col.default is not None and getattr(obj, col_name, None) is None:
            arg = getattr(col.default, "arg", None)
            if arg is not None and not callable(arg):
                setattr(obj, col_name, arg)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_db():
    db = MagicMock()
    db.refresh.side_effect = _refresh_handler
    # Default: queries return empty lists / None
    db.query.return_value.filter.return_value.first.return_value = None
    db.query.return_value.filter.return_value.all.return_value = []
    db.query.return_value.filter.return_value.count.return_value = 0
    db.query.return_value.filter.return_value.filter.return_value.first.return_value = None  # double-filter chain
    db.query.return_value.filter.return_value.filter.return_value.all.return_value = []
    db.query.return_value.offset.return_value.limit.return_value.all.return_value = []
    db.query.return_value.filter.return_value.offset.return_value.limit.return_value.all.return_value = []
    db.query.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []
    db.query.return_value.join.return_value.filter.return_value.all.return_value = []
    db.query.return_value.join.return_value.filter.return_value.count.return_value = 0
    db.query.return_value.options.return_value.filter.return_value.first.return_value = None
    db.query.return_value.options.return_value.filter.return_value.count.return_value = 0
    db.query.return_value.options.return_value.join.return_value.filter.return_value.all.return_value = []
    db.query.return_value.options.return_value.order_by.return_value.count.return_value = 0
    db.query.return_value.options.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []
    return db


@pytest.fixture
def client(mock_db):
    """Authenticated client with mocked DB."""
    app = create_app()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: JWT_PAYLOAD
    app.dependency_overrides[get_current_db_user] = fake_db_user
    return TestClient(app)


@pytest.fixture
def raw_client(mock_db):
    """Client without auth overrides – for testing 401/403 responses."""
    app = create_app()
    app.dependency_overrides[get_db] = lambda: mock_db
    return TestClient(app, raise_server_exceptions=False)
