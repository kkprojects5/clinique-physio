"""Shared test setup.

- Tests run on their OWN database ("<your database>_test"), created and migrated
  automatically, so they never touch your demo data and always start clean.
- Test-only secrets are set here, before the app is imported.
- Each API test runs inside a transaction that is rolled back at the end.
"""

import os

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


class _UrlOnly(BaseSettings):
    """Reads DATABASE_URL the same way the app does (environment or .env)."""

    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")
    database_url: str


_main_url = make_url(_UrlOnly().database_url)
TEST_DATABASE_URL = _main_url.set(database=f"{_main_url.database}_test")

os.environ["DATABASE_URL"] = TEST_DATABASE_URL.render_as_string(hide_password=False)
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("JWT_SECRET", "test-only-secret-not-used-anywhere-else-0123456789")
os.environ.setdefault("FIELD_ENCRYPTION_KEY", "rQ0kC2Jx0c3kWbqgJzQvYQe0m2lJ3H6xg5D2K8nWZ4o=")
os.environ.setdefault("COOKIE_SECURE", "false")  # the test client uses http, not https
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")  # turned on only in its own tests

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.db.session import engine, get_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def test_database():
    """Create the test database once (fresh), then apply all migrations."""
    admin = create_engine(_main_url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    name = TEST_DATABASE_URL.database
    with admin.connect() as connection:
        connection.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
        connection.execute(text(f'CREATE DATABASE "{name}"'))
    admin.dispose()

    command.upgrade(Config("alembic.ini"), "head")
    yield
    engine.dispose()


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
