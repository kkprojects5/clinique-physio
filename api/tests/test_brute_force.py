"""Brute-force protection: account lockout and rate limiting (B-AUTH-06, NFR-05)."""

from datetime import UTC, datetime, timedelta

import pyotp
import pytest

from app.core.config import settings
from app.core.crypto import encrypt
from app.core.rate_limit import limiter
from tests.test_login import PASSWORD, make_user
from tests.test_register import valid_payload

LOGIN = "/api/v1/auth/login"
VERIFY = "/api/v1/auth/mfa/verify"
LIMIT = settings.max_failed_logins


def login(client, email="patient@example.com", password=PASSWORD):
    return client.post(LOGIN, json={"email": email, "password": password})


def fail(client, times, email="patient@example.com"):
    for _ in range(times):
        assert login(client, email, "Wrong-Password-123").status_code == 401


def test_account_locks_after_too_many_wrong_passwords(client, db):
    user = make_user(db, "patient@example.com")
    fail(client, LIMIT)

    response = login(client)  # correct password, but the account is locked

    assert response.status_code == 401
    db.refresh(user)
    assert user.locked_until > datetime.now(UTC)


def test_locked_answer_looks_exactly_like_a_wrong_password(client, db):
    make_user(db, "patient@example.com")
    wrong_password = login(client, password="Wrong-Password-123")
    fail(client, LIMIT - 1)

    locked = login(client)

    assert locked.status_code == wrong_password.status_code
    assert locked.json() == wrong_password.json()  # reveals nothing to an attacker


def test_account_unlocks_after_the_lockout_period(client, db):
    user = make_user(db, "patient@example.com")
    fail(client, LIMIT)

    user.locked_until = datetime.now(UTC) - timedelta(seconds=1)  # 15 minutes went by
    db.commit()

    assert login(client).status_code == 200


def test_successful_login_resets_the_counter(client, db):
    user = make_user(db, "patient@example.com")
    fail(client, LIMIT - 1)

    assert login(client).status_code == 200
    db.refresh(user)
    assert user.failed_login_count == 0

    fail(client, LIMIT - 1)  # starts again from zero: still not locked
    assert login(client).status_code == 200


def test_wrong_mfa_codes_also_lock_staff_accounts(client, db):
    user = make_user(db, "therapist@example.com", role="therapist")
    secret = pyotp.random_base32()
    user.mfa_secret_enc = encrypt(secret)
    user.mfa_enabled_at = datetime.now(UTC)
    db.commit()
    ticket = login(client, "therapist@example.com").json()["mfa_token"]
    wrong = "000000" if pyotp.TOTP(secret).now() != "000000" else "111111"

    for _ in range(LIMIT):
        assert client.post(VERIFY, json={"mfa_token": ticket, "code": wrong}).status_code == 401

    right = pyotp.TOTP(secret).now()
    assert client.post(VERIFY, json={"mfa_token": ticket, "code": right}).status_code == 401
    db.refresh(user)
    assert user.locked_until is not None


@pytest.fixture
def rate_limited():
    """Turn rate limiting on for one test, with a fresh counter."""
    limiter.reset()
    limiter.enabled = True
    yield
    limiter.enabled = False
    limiter.reset()


def test_login_is_rate_limited_per_ip(client, rate_limited):
    statuses = [login(client, "nobody@example.com").status_code for _ in range(6)]

    assert statuses[:5] == [401] * 5
    assert statuses[5] == 429  # Too Many Requests


def test_registration_is_rate_limited_per_ip(client, rate_limited):
    statuses = [
        client.post(
            "/api/v1/auth/register", json=valid_payload(email=f"p{i}@example.com")
        ).status_code
        for i in range(6)
    ]

    assert statuses[:5] == [202] * 5
    assert statuses[5] == 429
