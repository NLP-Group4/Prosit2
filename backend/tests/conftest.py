"""
Shared test fixtures for auth-protected endpoint tests.

Provides a test database (SQLite in-memory), test user, and auth headers
so that test files don't need to set up auth individually.
"""

import uuid
import os
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("API_BUILDER_SKIP_DB_INIT", "1")

from backend.app.main import app
from backend.app.platform_db import Base, PlatformUser, get_db
from backend.app.platform_auth import _hash_password, _create_access_token


# ---------------------------------------------------------------------------
# In-memory SQLite for tests (no PostgreSQL needed)
# ---------------------------------------------------------------------------

TEST_ENGINE = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

# Enable foreign key enforcement for SQLite
@event.listens_for(TEST_ENGINE, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

TestSessionLocal = sessionmaker(bind=TEST_ENGINE, autocommit=False, autoflush=False)


def _override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Override the DB dependency for all tests
app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture(autouse=True)
def _reset_db():
    """Create fresh tables for every test."""
    Base.metadata.create_all(bind=TEST_ENGINE)
    yield
    Base.metadata.drop_all(bind=TEST_ENGINE)


@pytest.fixture
def db_session():
    """Provide a test database session."""
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def test_user(db_session):
    """Create a test user and return (user, plain_password)."""
    user = PlatformUser(
        email="test@example.com",
        hashed_password=_hash_password("testpass123"),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user, "testpass123"


@pytest.fixture
def auth_headers(test_user):
    """Return Authorization headers with a valid JWT for the test user."""
    user, _ = test_user
    token = _create_access_token(data={"sub": str(user.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def other_user(db_session):
    """Create a second user for cross-user security tests."""
    user = PlatformUser(
        email="other@example.com",
        hashed_password=_hash_password("otherpass123"),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user, "otherpass123"


@pytest.fixture
def other_auth_headers(other_user):
    """Auth headers for the other user."""
    user, _ = other_user
    token = _create_access_token(data={"sub": str(user.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def client():
    """Provide a FastAPI TestClient."""
    return TestClient(app)
