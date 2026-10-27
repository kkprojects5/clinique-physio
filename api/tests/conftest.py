"""Shared test setup.

Test-only secrets are set here, before the app is imported, so tests never
need the real keys. Each API test runs inside a transaction that is rolled
back at the end, so tests leave no data behind.
"""

import os

os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("JWT_SECRET", "test-only-secret-not-used-anywhere-else-0123456789")
os.environ.setdefault("FIELD_ENCRYPTION_KEY", "rQ0kC2Jx0c3kWbqgJzQvYQe0m2lJ3H6xg5D2K8nWZ4o=")
os.environ.setdefault("COOKIE_SECURE", "false")  # the test client uses http, not https
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")  # turned on only in its own tests

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.db.session import engine, get_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture
def db():
    """A session whose changes are all undone after the test."""
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db):
    """An HTTP client for the API that uses the test session."""
    app.dependency_overrides[get_db] = lambda: db
    yield TestClient(app)
    app.dependency_overrides.clear()
