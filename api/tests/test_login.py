"""Login, token refresh with rotation, logout and /me (B-AUTH-02)."""

from datetime import UTC, datetime, timedelta

import jwt
import pytest
from sqlalchemy import select

from app.core.config import settings
from app.core.security import create_token, hash_password
from app.models import RefreshToken, User

PASSWORD = "Correct-Horse-Battery-9"
LOGIN = "/api/v1/auth/login"
REFRESH = "/api/v1/auth/refresh"
LOGOUT = "/api/v1/auth/logout"
ME = "/api/v1/me"


def make_user(db, email, role="patient", verified=True, active=True):
    user = User(
        email=email,
        password_hash=hash_password(PASSWORD),
        role=role,
        is_active=active,
        email_verified_at=datetime.now(UTC) if verified else None,
    )
    db.add(user)
    db.commit()
    return user


@pytest.fixture
def patient(db):
    return make_user(db, "patient@example.com")


def login(client, email="patient@example.com", password=PASSWORD):
    return client.post(LOGIN, json={"email": email, "password": password})


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def test_login_returns_access_token_and_httponly_refresh_cookie(client, patient):
    response = login(client)

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    cookie = response.headers["set-cookie"]
    assert "refresh_token=" in cookie
    assert "HttpOnly" in cookie
    assert "Path=/api/v1/auth" in cookie
    assert "refresh_token" not in response.json()  # never in the body: JavaScript can't read it


def test_access_token_lasts_at_most_10_minutes(client, patient):
    token = login(client).json()["access_token"]

    payload = jwt.decode(token, options={"verify_signature": False})
    assert payload["exp"] - payload["iat"] <= 10 * 60
    assert payload["role"] == "patient"


def test_me_works_with_token_and_refuses_without(client, patient):
    token = login(client).json()["access_token"]

    assert client.get(ME, headers=bearer(token)).json()["email"] == "patient@example.com"
    assert client.get(ME).status_code == 401
    assert client.get(ME, headers=bearer("garbage")).status_code == 401


def test_wrong_password_and_unknown_email_get_the_same_answer(client, patient):
    wrong_password = login(client, password="Wrong-Password-123")
    unknown_email = login(client, email="nobody@example.com")

    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()


def test_email_must_be_verified(client, db):
    make_user(db, "new@example.com", verified=False)

    assert login(client, email="new@example.com").status_code == 403


def test_inactive_account_cannot_log_in(client, db):
    make_user(db, "gone@example.com", active=False)

    assert login(client, email="gone@example.com").status_code == 401


def test_other_token_types_are_refused_as_access_token(client, patient):
    email_token = create_token(str(patient.id), "email_verify", timedelta(hours=1))

    assert client.get(ME, headers=bearer(email_token)).status_code == 401


def test_expired_access_token_is_refused(client, patient):
    expired = create_token(str(patient.id), "access", timedelta(seconds=-1))

    assert client.get(ME, headers=bearer(expired)).status_code == 401


def test_refresh_gives_new_tokens_and_old_refresh_token_stops_working(client, patient):
    login(client)
    old_refresh = client.cookies.get("refresh_token")

    response = client.post(REFRESH)

    assert response.status_code == 200
    assert client.get(ME, headers=bearer(response.json()["access_token"])).status_code == 200
    assert client.cookies.get("refresh_token") != old_refresh

    client.cookies.set("refresh_token", old_refresh, path="/api/v1/auth")
    assert client.post(REFRESH).status_code == 401


def test_reusing_an_old_refresh_token_cancels_all_sessions(client, db, patient):
    login(client)
    stolen = client.cookies.get("refresh_token")
    client.post(REFRESH)  # the real user refreshes: 'stolen' is now an old token
    current = client.cookies.get("refresh_token")

    client.cookies.set("refresh_token", stolen, path="/api/v1/auth")
    assert client.post(REFRESH).status_code == 401  # the thief is refused...

    client.cookies.set("refresh_token", current, path="/api/v1/auth")
    assert client.post(REFRESH).status_code == 401  # ...and the real session is cancelled too
    active = db.scalars(
        select(RefreshToken).where(
            RefreshToken.user_id == patient.id, RefreshToken.revoked_at.is_(None)
        )
    ).all()
    assert active == []


def test_logout_revokes_the_refresh_token(client, patient):
    login(client)
    refresh_token = client.cookies.get("refresh_token")

    response = client.post(LOGOUT)

    assert response.status_code == 200
    client.cookies.set("refresh_token", refresh_token, path="/api/v1/auth")
    assert client.post(REFRESH).status_code == 401


def test_refresh_without_cookie_is_refused(client):
    assert client.post(REFRESH).status_code == 401


def test_staff_session_expires_after_15_minutes_of_inactivity(client, db):
    therapist = make_user(db, "therapist@example.com", role="therapist")
    login(client, email="therapist@example.com")

    stored = db.scalar(select(RefreshToken).where(RefreshToken.user_id == therapist.id))
    lifetime = stored.expires_at - stored.created_at
    assert lifetime <= timedelta(minutes=settings.staff_inactivity_minutes, seconds=5)

    stored.expires_at = datetime.now(UTC) - timedelta(seconds=1)  # 15 minutes went by
    db.commit()
    assert client.post(REFRESH).status_code == 401


def test_patient_session_lasts_longer(client, db, patient):
    login(client)

    stored = db.scalar(select(RefreshToken).where(RefreshToken.user_id == patient.id))
    assert stored.expires_at - stored.created_at > timedelta(days=6)
