"""Patient registration and email verification (B-AUTH-01, B-AUTH-03)."""

from datetime import timedelta

from sqlalchemy import select

from app.core.config import settings
from app.core.crypto import decrypt
from app.core.security import create_token
from app.models import Consent, Patient, User

URL = "/api/v1/auth/register"


def valid_payload(**changes):
    payload = {
        "email": "Marie.Tremblay@example.com",
        "password": "Correct-Horse-Battery-9",
        "first_name": "Marie",
        "last_name": "Tremblay",
        "date_of_birth": "1988-05-17",
        "phone": "514-555-0142",
        "language": "fr",
        "emergency_contact": "Luc Tremblay 514-555-0199",
        "accept_privacy_policy": True,
        "accept_electronic_comms": True,
    }
    payload.update(changes)
    return payload


def get_user(db, email="marie.tremblay@example.com"):
    return db.scalar(select(User).where(User.email == email))


def test_register_creates_patient_user_and_consents(client, db):
    response = client.post(URL, json=valid_payload())

    assert response.status_code == 202
    user = get_user(db)
    assert user.role == "patient"
    assert user.language == "fr"
    assert user.email_verified_at is None
    patient = db.scalar(select(Patient).where(Patient.user_id == user.id))
    assert patient.last_name == "Tremblay"
    consents = db.scalars(select(Consent).where(Consent.user_id == user.id)).all()
    assert {c.type for c in consents} == {"privacy_policy", "electronic_comms"}
    assert all(c.version == settings.privacy_policy_version for c in consents)
    assert all(c.granted_at is not None for c in consents)


def test_password_is_stored_as_argon2id_hash(client, db):
    client.post(URL, json=valid_payload())

    user = get_user(db)
    assert user.password_hash.startswith("$argon2id$")
    assert "Correct-Horse-Battery-9" not in user.password_hash


def test_emergency_contact_is_encrypted(client, db):
    client.post(URL, json=valid_payload())

    patient = db.scalar(select(Patient).where(Patient.user_id == get_user(db).id))
    assert b"Luc Tremblay" not in patient.emergency_contact_enc
    assert decrypt(patient.emergency_contact_enc) == "Luc Tremblay 514-555-0199"


def test_existing_email_gets_same_answer_and_no_second_account(client, db):
    first = client.post(URL, json=valid_payload())
    second = client.post(URL, json=valid_payload(first_name="Someone", last_name="Else"))

    assert second.status_code == first.status_code == 202
    assert second.json() == first.json()  # no user enumeration
    users = db.scalars(select(User).where(User.email == "marie.tremblay@example.com")).all()
    assert len(users) == 1


def test_privacy_policy_must_be_accepted(client, db):
    response = client.post(URL, json=valid_payload(accept_privacy_policy=False))

    assert response.status_code == 422
    assert get_user(db) is None


def test_electronic_comms_consent_is_optional(client, db):
    client.post(URL, json=valid_payload(accept_electronic_comms=False))

    consents = db.scalars(select(Consent).where(Consent.user_id == get_user(db).id)).all()
    assert [c.type for c in consents] == ["privacy_policy"]


def test_weak_passwords_are_refused(client, db):
    too_short = client.post(URL, json=valid_payload(password="Short-1"))
    contains_email = client.post(URL, json=valid_payload(password="marie.tremblay-2026!"))

    assert too_short.status_code == 422
    assert contains_email.status_code == 422
    assert get_user(db) is None


def test_birth_date_in_the_future_is_refused(client):
    response = client.post(URL, json=valid_payload(date_of_birth="2999-01-01"))

    assert response.status_code == 422


def test_role_cannot_be_chosen_by_the_client(client, db):
    client.post(URL, json=valid_payload(role="admin"))

    assert get_user(db).role == "patient"


def test_verify_email_with_valid_token(client, db):
    client.post(URL, json=valid_payload())
    user = get_user(db)
    token = create_token(str(user.id), "email_verify", timedelta(hours=1))

    response = client.post("/api/v1/auth/verify-email", json={"token": token})

    assert response.status_code == 200
    db.refresh(user)
    assert user.email_verified_at is not None


def test_verify_email_refuses_bad_expired_or_wrong_purpose_tokens(client, db):
    client.post(URL, json=valid_payload())
    user_id = str(get_user(db).id)
    expired = create_token(user_id, "email_verify", timedelta(seconds=-1))
    wrong_purpose = create_token(user_id, "password_reset", timedelta(hours=1))

    for token in ["not-a-token", expired, wrong_purpose]:
        response = client.post("/api/v1/auth/verify-email", json={"token": token})
        assert response.status_code == 400

    assert get_user(db).email_verified_at is None
