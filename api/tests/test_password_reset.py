"""Password reset by email link, without user enumeration (B-AUTH-03, US-AUTH-03b)."""

import re
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.core.rate_limit import limiter
from app.models import PasswordResetToken, RefreshToken
from app.services import password_reset_service
from tests.test_login import LOGIN, PASSWORD, REFRESH, login, make_user

FORGOT = "/api/v1/auth/password/forgot"
RESET = "/api/v1/auth/password/reset"
NEW_PASSWORD = "Brand-New-Secret-Phrase-42"


@pytest.fixture
def outbox(monkeypatch):
    """Collect the emails instead of sending them."""
    sent = []
    monkeypatch.setattr(
        password_reset_service, "send_email", lambda to, subject, body: sent.append((to, body))
    )
    return sent


@pytest.fixture
def patient(db):
    return make_user(db, "patient@example.com")


def ask_link(client, outbox, email="patient@example.com"):
    """Ask for a reset and return the token from the email's link."""
    client.post(FORGOT, json={"email": email})
    return re.search(r"token=([\w-]+)", outbox[-1][1]).group(1)


def reset(client, token, password=NEW_PASSWORD):
    return client.post(RESET, json={"token": token, "new_password": password})


def test_same_answer_whether_or_not_the_account_exists(client, patient, outbox):
    known = client.post(FORGOT, json={"email": "patient@example.com"})
    unknown = client.post(FORGOT, json={"email": "nobody@example.com"})

    assert known.status_code == unknown.status_code == 202
    assert known.json() == unknown.json()
    assert [to for to, _ in outbox] == ["patient@example.com"]  # only real accounts get mail


def test_inactive_account_gets_no_link(client, db, outbox):
    make_user(db, "gone@example.com", active=False)

    assert client.post(FORGOT, json={"email": "gone@example.com"}).status_code == 202
    assert outbox == []


def test_only_a_hash_of_the_token_is_stored(client, db, patient, outbox):
    token = ask_link(client, outbox)

    stored = db.scalars(select(PasswordResetToken)).all()
    assert len(stored) == 1
    assert stored[0].token_hash != token
    assert token not in stored[0].token_hash


def test_reset_changes_the_password(client, patient, outbox):
    token = ask_link(client, outbox)

    response = reset(client, token)

    assert response.status_code == 200
    assert login(client).status_code == 401  # old password refused
    assert login(client, password=NEW_PASSWORD).status_code == 200
    assert "modifié" in outbox[-1][1]  # owner told that the password changed (French default)


def test_link_works_only_once(client, patient, outbox):
    token = ask_link(client, outbox)

    assert reset(client, token).status_code == 200
    assert reset(client, token, "Another-Long-Password-77").status_code == 400


def test_expired_link_is_refused(client, db, patient, outbox):
    token = ask_link(client, outbox)
    stored = db.scalar(select(PasswordResetToken))
    stored.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    db.commit()

    assert reset(client, token).status_code == 400
    assert login(client).status_code == 200  # password unchanged


def test_link_expires_after_30_minutes(client, db, patient, outbox):
    ask_link(client, outbox)
    stored = db.scalar(select(PasswordResetToken))

    assert stored.expires_at - stored.created_at <= timedelta(minutes=30, seconds=5)


def test_new_request_cancels_the_previous_link(client, patient, outbox):
    old = ask_link(client, outbox)
    new = ask_link(client, outbox)

    assert reset(client, old).status_code == 400
    assert reset(client, new).status_code == 200


def test_unknown_or_garbage_token_is_refused(client, patient):
    assert reset(client, "not-a-real-token").status_code == 400


def test_reset_cancels_every_session(client, db, patient, outbox):
    login(client)  # an open session (maybe an attacker's)
    refresh_cookie = client.cookies.get("refresh_token")
    token = ask_link(client, outbox)

    reset(client, token)

    assert db.scalars(select(RefreshToken).where(RefreshToken.revoked_at.is_(None))).all() == []
    client.cookies.set("refresh_token", refresh_cookie, path="/api/v1/auth")
    assert client.post(REFRESH).status_code == 401


def test_weak_password_is_refused_and_link_stays_usable(client, patient, outbox):
    token = ask_link(client, outbox)

    assert reset(client, token, "short").status_code == 422  # under 12 characters
    assert reset(client, token, "patient-is-my-password").status_code == 422  # contains email
    assert reset(client, token).status_code == 200


def test_reset_unlocks_a_locked_account(client, db, patient, outbox):
    patient.locked_until = datetime.now(UTC) + timedelta(minutes=15)
    db.commit()
    token = ask_link(client, outbox)

    reset(client, token)

    assert login(client, password=NEW_PASSWORD).status_code == 200


def test_staff_still_need_their_code_after_a_reset(client, db, outbox):
    make_user(db, "therapist@example.com", role="therapist")
    token = ask_link(client, outbox, "therapist@example.com")

    reset(client, token)
    response = client.post(LOGIN, json={"email": "therapist@example.com", "password": NEW_PASSWORD})

    assert response.status_code == 200
    assert response.json()["mfa_required"] is True
    assert "access_token" not in response.json()


def test_old_password_hash_is_not_kept(client, db, patient, outbox):
    old_hash = patient.password_hash
    reset(client, ask_link(client, outbox))
    db.refresh(patient)

    assert patient.password_hash != old_hash
    assert patient.password_hash.startswith("$argon2id$")
    assert PASSWORD not in patient.password_hash


@pytest.fixture
def rate_limited():
    limiter.reset()
    limiter.enabled = True
    yield
    limiter.enabled = False
    limiter.reset()


def test_forgot_password_is_rate_limited_per_ip(client, rate_limited, outbox):
    statuses = [
        client.post(FORGOT, json={"email": "nobody@example.com"}).status_code for _ in range(6)
    ]

    assert statuses[:5] == [202] * 5
    assert statuses[5] == 429


def test_reset_is_rate_limited_per_ip(client, rate_limited):
    statuses = [reset(client, f"guess-{i}").status_code for i in range(6)]

    assert statuses[:5] == [400] * 5
    assert statuses[5] == 429
