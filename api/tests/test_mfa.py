"""Mandatory two-factor authentication for staff (B-AUTH-04).

AC: staff endpoints refuse tokens without the MFA claim.
"""

from datetime import UTC, datetime, timedelta

import jwt
import pyotp
import pytest

from app.core.crypto import decrypt, encrypt
from app.core.security import create_token
from tests.test_login import PASSWORD, bearer, make_user

LOGIN = "/api/v1/auth/login"
SETUP = "/api/v1/auth/mfa/setup"
VERIFY = "/api/v1/auth/mfa/verify"
STAFF = "/api/v1/staff/session"
REFRESH = "/api/v1/auth/refresh"


def login(client, email):
    return client.post(LOGIN, json={"email": email, "password": PASSWORD})


@pytest.fixture
def enrolled_therapist(db):
    """A therapist who already set up the authenticator app."""
    user = make_user(db, "therapist@example.com", role="therapist")
    secret = pyotp.random_base32()
    user.mfa_secret_enc = encrypt(secret)
    user.mfa_enabled_at = datetime.now(UTC)
    db.commit()
    return user, secret


def code_for(secret):
    return pyotp.TOTP(secret).now()


@pytest.mark.parametrize("role", ["therapist", "front_desk", "admin"])
def test_staff_password_alone_gives_no_tokens(client, db, role):
    make_user(db, f"{role}@example.com", role=role)

    response = login(client, f"{role}@example.com")

    assert response.status_code == 200
    body = response.json()
    assert body["mfa_required"] is True
    assert "access_token" not in body
    assert "set-cookie" not in response.headers


def test_first_login_enrolment_then_session_with_mfa(client, db):
    user = make_user(db, "new.therapist@example.com", role="therapist")
    challenge = login(client, "new.therapist@example.com").json()
    assert challenge["mfa_setup_required"] is True

    setup = client.post(SETUP, json={"mfa_token": challenge["mfa_token"]})
    assert setup.status_code == 200
    secret = setup.json()["secret"]
    assert setup.json()["otpauth_uri"].startswith("otpauth://totp/")

    db.refresh(user)
    assert secret.encode() not in user.mfa_secret_enc  # stored encrypted
    assert decrypt(user.mfa_secret_enc) == secret

    response = client.post(
        VERIFY, json={"mfa_token": challenge["mfa_token"], "code": code_for(secret)}
    )

    assert response.status_code == 200
    token = response.json()["access_token"]
    assert jwt.decode(token, options={"verify_signature": False})["mfa"] is True
    assert "refresh_token=" in response.headers["set-cookie"]
    assert client.get(STAFF, headers=bearer(token)).status_code == 200
    db.refresh(user)
    assert user.mfa_enabled_at is not None


def test_enrolled_staff_login_with_code(client, enrolled_therapist):
    _, secret = enrolled_therapist
    challenge = login(client, "therapist@example.com").json()
    assert challenge["mfa_setup_required"] is False

    response = client.post(
        VERIFY, json={"mfa_token": challenge["mfa_token"], "code": code_for(secret)}
    )

    assert response.status_code == 200


def test_wrong_code_is_refused(client, enrolled_therapist):
    _, secret = enrolled_therapist
    ticket = login(client, "therapist@example.com").json()["mfa_token"]
    wrong = "000000" if code_for(secret) != "000000" else "111111"

    response = client.post(VERIFY, json={"mfa_token": ticket, "code": wrong})

    assert response.status_code == 401
    assert "set-cookie" not in response.headers


def test_a_code_cannot_be_used_twice(client, enrolled_therapist):
    _, secret = enrolled_therapist
    code = code_for(secret)
    first = login(client, "therapist@example.com").json()["mfa_token"]
    second = login(client, "therapist@example.com").json()["mfa_token"]

    assert client.post(VERIFY, json={"mfa_token": first, "code": code}).status_code == 200
    assert client.post(VERIFY, json={"mfa_token": second, "code": code}).status_code == 401


def test_enrolment_cannot_be_restarted_with_only_a_password(client, enrolled_therapist):
    ticket = login(client, "therapist@example.com").json()["mfa_token"]

    assert client.post(SETUP, json={"mfa_token": ticket}).status_code == 409


def test_expired_or_wrong_ticket_is_refused(client, enrolled_therapist):
    user, secret = enrolled_therapist
    expired = create_token(str(user.id), "mfa_pending", timedelta(seconds=-1))
    wrong_purpose = create_token(str(user.id), "email_verify", timedelta(minutes=5))

    for ticket in [expired, wrong_purpose, "garbage"]:
        response = client.post(VERIFY, json={"mfa_token": ticket, "code": code_for(secret)})
        assert response.status_code == 401


def test_patient_ticket_cannot_be_used_for_staff_mfa(client, db):
    patient = make_user(db, "patient@example.com")
    ticket = create_token(str(patient.id), "mfa_pending", timedelta(minutes=5))

    assert client.post(SETUP, json={"mfa_token": ticket}).status_code == 401


def test_staff_endpoint_refuses_staff_token_without_mfa_claim(client, enrolled_therapist):
    user, _ = enrolled_therapist
    no_mfa = create_token(
        str(user.id), "access", timedelta(minutes=5), extra={"role": "therapist", "mfa": False}
    )

    response = client.get(STAFF, headers=bearer(no_mfa))

    assert response.status_code == 403
    assert response.json()["detail"] == "Two-factor authentication is required."


def test_staff_endpoint_refuses_patients_even_with_mfa_claim(client, db):
    patient = make_user(db, "patient@example.com")
    forged = create_token(
        str(patient.id), "access", timedelta(minutes=5), extra={"role": "admin", "mfa": True}
    )

    assert client.get(STAFF, headers=bearer(forged)).status_code == 403  # role read from DB


def test_staff_refresh_keeps_mfa(client, enrolled_therapist):
    _, secret = enrolled_therapist
    ticket = login(client, "therapist@example.com").json()["mfa_token"]
    client.post(VERIFY, json={"mfa_token": ticket, "code": code_for(secret)})

    token = client.post(REFRESH).json()["access_token"]

    assert client.get(STAFF, headers=bearer(token)).status_code == 200


def test_patients_still_log_in_without_mfa(client, db):
    make_user(db, "patient@example.com")

    response = login(client, "patient@example.com")

    assert "access_token" in response.json()
