"""Consent management (Law 25): the patient sees, gives and withdraws consents."""

from datetime import UTC, datetime

from sqlalchemy import select

from app.core.config import settings
from app.models import AuditLog, Consent, User
from app.services import consent_service
from tests.test_clinical import as_staff
from tests.test_login import make_user
from tests.test_schedules import make_patient, patient_headers

MINE = "/api/v1/me/consents"
COMMS = f"{MINE}/electronic_comms"
POLICY = f"{MINE}/privacy_policy"


def registered(db, name="Marie", comms=False, version=None):
    """A patient as created at registration: the policy accepted, messages if ticked."""
    patient = make_patient(db, name)
    db.add(
        Consent(
            user_id=patient.user_id,
            type="privacy_policy",
            version=version or settings.privacy_policy_version,
        )
    )
    if comms:
        db.add(
            Consent(
                user_id=patient.user_id,
                type="electronic_comms",
                version=settings.privacy_policy_version,
            )
        )
    db.commit()
    return patient


def by_type(response):
    return {c["type"]: c for c in response.json()}


def test_patient_sees_both_consents(client, db):
    marie = registered(db)

    response = client.get(MINE, headers=patient_headers(marie))

    assert response.status_code == 200
    consents = by_type(response)
    policy, comms = consents["privacy_policy"], consents["electronic_comms"]
    assert policy["given"] and policy["up_to_date"]
    assert policy["version"] == settings.privacy_policy_version
    assert comms["given"] is False and comms["granted_at"] is None


def test_patient_withdraws_electronic_comms(client, db):
    marie = registered(db, comms=True)

    response = client.put(COMMS, json={"given": False}, headers=patient_headers(marie))

    assert response.status_code == 200
    assert response.json()["given"] is False and response.json()["revoked_at"] is not None
    row = db.scalar(select(Consent).where(Consent.type == "electronic_comms"))
    assert row.revoked_at is not None  # kept, with its withdrawal date, for the history
    entry = db.scalar(select(AuditLog).where(AuditLog.action == "consent_withdrawn"))
    assert entry.patient_id == marie.id
    user = db.get(User, marie.user_id)
    assert consent_service.wants_electronic_comms(db, user) is False


def test_giving_again_adds_a_new_row(client, db):
    marie = registered(db, comms=True)
    client.put(COMMS, json={"given": False}, headers=patient_headers(marie))

    response = client.put(COMMS, json={"given": True}, headers=patient_headers(marie))

    assert response.json()["given"] is True and response.json()["revoked_at"] is None
    rows = db.scalars(select(Consent).where(Consent.type == "electronic_comms")).all()
    assert len(rows) == 2  # the withdrawn one stays in the history
    assert db.scalar(select(AuditLog).where(AuditLog.action == "consent_given")) is not None


def test_repeating_the_same_choice_changes_nothing(client, db):
    marie = registered(db)

    client.put(COMMS, json={"given": False}, headers=patient_headers(marie))

    assert db.scalar(select(Consent).where(Consent.type == "electronic_comms")) is None
    assert db.scalar(select(AuditLog).where(AuditLog.resource_type == "consent")) is None


def test_patient_accepts_a_new_policy_version(client, db):
    marie = registered(db, version="2025-01")
    before = by_type(client.get(MINE, headers=patient_headers(marie)))["privacy_policy"]
    assert before["given"] and not before["up_to_date"]

    response = client.post(POLICY, headers=patient_headers(marie))

    assert response.status_code == 200
    assert response.json()["up_to_date"] is True
    versions = db.scalars(
        select(Consent.version).where(Consent.type == "privacy_policy").order_by(Consent.version)
    ).all()
    assert versions == ["2025-01", settings.privacy_policy_version]  # both kept, as proof


def test_the_privacy_policy_cannot_be_withdrawn_here(client, db):
    marie = registered(db)

    response = client.put(
        f"{MINE}/privacy_policy", json={"given": False}, headers=patient_headers(marie)
    )

    assert response.status_code == 405  # only a deletion request closes the account
    assert consent_service.my_consents(db, db.get(User, marie.user_id))[0].given


def test_only_own_consents_are_changed(client, db):
    marie = registered(db, "Marie", comms=True)
    paul = registered(db, "Paul", comms=True)

    client.put(COMMS, json={"given": False}, headers=patient_headers(marie))

    assert consent_service.wants_electronic_comms(db, db.get(User, paul.user_id))
    assert not consent_service.wants_electronic_comms(db, db.get(User, marie.user_id))


def test_staff_have_no_consents_page(client, db):
    desk = make_user(db, "accueil-consent@example.com", role="front_desk")

    response = client.get(MINE, headers=as_staff(desk, role="front_desk"))

    assert response.status_code == 403


def test_latest_given_row_wins_over_an_older_withdrawn_one(db):
    marie = registered(db)
    user = db.get(User, marie.user_id)
    db.add(
        Consent(
            user_id=user.id,
            type="electronic_comms",
            version="2025-01",
            granted_at=datetime(2025, 1, 1, tzinfo=UTC),
            revoked_at=datetime(2025, 6, 1, tzinfo=UTC),
        )
    )
    db.add(
        Consent(
            user_id=user.id,
            type="electronic_comms",
            version="2026-10",
            granted_at=datetime(2026, 2, 1, tzinfo=UTC),
        )
    )
    db.commit()

    assert consent_service.wants_electronic_comms(db, user)
