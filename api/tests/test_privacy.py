"""Law 25: privacy requests (B-ADM-04) and confidentiality incident register (B-ADM-05)."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from app.models import AuditLog, Consent, Incident, Patient, PrivacyRequest, RefreshToken, User
from app.services import notification_service, privacy_service
from tests.test_admin import ADMIN  # noqa: F401
from tests.test_booking import at, clinic, place  # noqa: F401  (fixture)
from tests.test_clinical import as_staff
from tests.test_login import make_user
from tests.test_schedules import make_patient, patient_headers

MINE = "/api/v1/me/privacy-requests"
REQUESTS = "/api/v1/admin/privacy-requests"
INCIDENTS = "/api/v1/admin/incidents"


@pytest.fixture
def admin(db):
    return make_user(db, f"admin-{uuid.uuid4().hex[:6]}@example.com", role="admin")


@pytest.fixture
def headers(admin):
    return as_staff(admin, role="admin", app="web")


@pytest.fixture
def outbox(monkeypatch):
    sent = []
    monkeypatch.setattr(
        notification_service, "send_email", lambda to, subject, body: sent.append((to, body))
    )
    return sent


def ask(client, patient, kind="access", details="Je veux voir mes renseignements."):
    return client.post(
        MINE, json={"type": kind, "details": details}, headers=patient_headers(patient)
    )


# --- Patient side -------------------------------------------------------------------------------


def test_patient_asks_and_gets_a_30_day_deadline(client, db):
    marie = make_patient(db, "Marie")

    response = ask(client, marie)

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "received"
    requested = datetime.fromisoformat(body["requested_at"])
    due = datetime.fromisoformat(body["due_at"])
    assert due - requested == timedelta(days=30)
    assert [r["id"] for r in client.get(MINE, headers=patient_headers(marie)).json()] == [
        body["id"]
    ]


def test_one_open_request_of_each_type(client, db):
    marie = make_patient(db, "Marie")
    ask(client, marie)

    assert ask(client, marie).status_code == 409
    assert ask(client, marie, "correction").status_code == 201


def test_patients_see_only_their_own_requests(client, db):
    marie, paul = make_patient(db, "Marie"), make_patient(db, "Paul")
    ask(client, marie)

    assert client.get(MINE, headers=patient_headers(paul)).json() == []


@pytest.mark.parametrize("role", ["therapist", "front_desk"])
def test_staff_cannot_use_or_see_privacy_requests(client, db, role):
    user = make_user(db, f"{role}-{uuid.uuid4().hex[:6]}@example.com", role=role)

    assert client.get(REQUESTS, headers=as_staff(user, role=role)).status_code == 403
    assert client.get(INCIDENTS, headers=as_staff(user, role=role)).status_code == 403


# --- Administrator: follow-up -------------------------------------------------------------------


def test_admin_sees_open_requests_first_with_overdue_ones(client, db, headers):
    marie, paul = make_patient(db, "Marie"), make_patient(db, "Paul")
    old_id = ask(client, marie).json()["id"]
    ask(client, paul, "correction")
    late = db.get(PrivacyRequest, uuid.UUID(old_id))
    late.due_at = datetime.now(UTC) - timedelta(days=1)
    db.commit()

    listed = client.get(REQUESTS, headers=headers).json()

    assert listed[0]["id"] == old_id and listed[0]["overdue"] is True
    assert listed[0]["patient_name"] == "Marie Test"
    assert listed[1]["overdue"] is False


def test_answering_needs_a_written_answer_and_tells_the_patient(client, db, headers, outbox):
    marie = make_patient(db, "Marie")
    request_id = ask(client, marie, "correction", "Mon numéro a changé.").json()["id"]

    empty = client.patch(f"{REQUESTS}/{request_id}", json={"status": "completed"}, headers=headers)
    done = client.patch(
        f"{REQUESTS}/{request_id}",
        json={"status": "completed", "outcome": "Numéro de téléphone corrigé."},
        headers=headers,
    )
    again = client.patch(
        f"{REQUESTS}/{request_id}", json={"status": "refused", "outcome": "x"}, headers=headers
    )

    assert empty.status_code == 422
    assert done.status_code == 200 and done.json()["completed_at"]
    assert again.status_code == 409
    to, body = outbox[0]
    assert to == db.get(User, marie.user_id).email
    assert "Numéro de téléphone corrigé." in body and "Commission d'accès" in body


def test_export_for_an_access_request_has_no_clinical_notes(client, db, headers, clinic):  # noqa: F811
    marie = make_patient(db, "Marie")
    place(db, marie, clinic["anne"], clinic["treatment"], at(10))
    request_id = ask(client, marie).json()["id"]

    export = client.get(f"{REQUESTS}/{request_id}/export", headers=headers)

    assert export.status_code == 200
    data = export.json()
    assert data["profile"]["first_name"] == "Marie"
    assert len(data["appointments"]) == 1
    assert "notes" not in data and "soap" not in str(data).lower()
    entries = db.scalars(select(AuditLog).where(AuditLog.action == "export")).all()
    assert entries and entries[0].patient_id == marie.id


def test_export_only_for_access_requests(client, db, headers):
    marie = make_patient(db, "Marie")
    request_id = ask(client, marie, "deletion").json()["id"]

    assert client.get(f"{REQUESTS}/{request_id}/export", headers=headers).status_code == 422


# --- Deletion -----------------------------------------------------------------------------------


def test_deletion_without_health_record_anonymizes_everything(client, db, headers):
    marie = make_patient(db, "Marie")
    db.add(
        RefreshToken(
            user_id=marie.user_id,
            token_hash="y" * 64,
            expires_at=datetime.now(UTC) + timedelta(days=1),
        )
    )
    db.add(Consent(user_id=marie.user_id, type="electronic_comms", version="1"))
    db.commit()
    request_id = ask(client, marie, "deletion").json()["id"]

    response = client.post(f"{REQUESTS}/{request_id}/erase", headers=headers)

    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    db.expire_all()
    user = db.get(User, marie.user_id)
    patient = db.get(Patient, marie.id)
    assert user.is_active is False and user.email.startswith("erased-")
    assert patient.first_name == "Anonymized" and patient.phone == "—"
    token = db.scalar(select(RefreshToken).where(RefreshToken.user_id == user.id))
    assert token.revoked_at is not None
    consent = db.scalar(select(Consent).where(Consent.user_id == user.id))
    assert consent.revoked_at is not None
    # The old login no longer works.
    assert client.get(MINE, headers=patient_headers(marie)).status_code == 401


def test_deletion_keeps_the_health_record_with_the_reason(client, db, headers, clinic):  # noqa: F811
    marie = make_patient(db, "Marie")
    place(db, marie, clinic["anne"], clinic["treatment"], at(10))
    request_id = ask(client, marie, "deletion").json()["id"]

    answer = client.post(f"{REQUESTS}/{request_id}/erase", headers=headers).json()

    db.expire_all()
    patient = db.get(Patient, marie.id)
    assert patient.first_name == "Marie"  # kept with the clinical record
    assert patient.phone == "—"
    assert "kept until" in answer["outcome"] and "5 years after the last visit" in answer["outcome"]


def test_deletion_is_completed_only_by_the_erase_action(client, db, headers):
    marie = make_patient(db, "Marie")
    request_id = ask(client, marie, "deletion").json()["id"]

    response = client.patch(
        f"{REQUESTS}/{request_id}", json={"status": "completed", "outcome": "fait"}, headers=headers
    )

    assert response.status_code == 422


# --- Incident register --------------------------------------------------------------------------


INCIDENT = {
    "occurred_at": "2026-11-10T14:00:00Z",
    "discovered_at": "2026-11-12T09:00:00Z",
    "description": "Un courriel de rappel a été envoyé au mauvais patient.",
    "data_categories": "Nom, date et heure d'un rendez-vous",
    "people_affected": 1,
    "risk_level": "serious",
    "measures": "Courriel supprimé par le destinataire; procédure d'envoi vérifiée.",
}


def test_record_an_incident_and_see_missing_notifications(client, db, headers):
    response = client.post(INCIDENTS, json=INCIDENT, headers=headers)

    assert response.status_code == 201
    assert response.json()["to_notify"] == ["cai", "persons"]
    assert db.scalar(select(AuditLog).where(AuditLog.resource_type == "incident")) is not None


def test_notifications_are_recorded_later(client, headers):
    incident_id = client.post(INCIDENTS, json=INCIDENT, headers=headers).json()["id"]

    response = client.patch(
        f"{INCIDENTS}/{incident_id}",
        json={
            "cai_notified_at": "2026-11-13T10:00:00Z",
            "persons_notified_at": "2026-11-13T11:00:00Z",
        },
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["to_notify"] == []


def test_low_risk_incident_needs_no_notification(client, headers):
    response = client.post(INCIDENTS, json={**INCIDENT, "risk_level": "low"}, headers=headers)

    assert response.json()["to_notify"] == []


@pytest.mark.parametrize(
    "change",
    [
        {"discovered_at": "2026-11-09T09:00:00Z"},  # before the incident
        {"occurred_at": "2099-01-01T00:00:00Z", "discovered_at": "2099-01-02T00:00:00Z"},  # future
        {"risk_level": "medium"},
        {"description": ""},
    ],
)
def test_invalid_incidents_are_refused(client, headers, change):
    assert client.post(INCIDENTS, json={**INCIDENT, **change}, headers=headers).status_code == 422


def test_incident_entries_can_never_be_deleted(client, db, headers):
    incident_id = client.post(INCIDENTS, json=INCIDENT, headers=headers).json()["id"]

    with pytest.raises(DBAPIError, match="cannot be deleted"):
        db.execute(text("DELETE FROM incident_register WHERE id = :id"), {"id": incident_id})
    db.rollback()
    assert db.get(Incident, uuid.UUID(incident_id)) is not None


def test_service_lists_incidents_newest_first(db, admin):
    first = privacy_service.record_incident(
        db,
        admin,
        {
            **INCIDENT,
            "occurred_at": datetime(2026, 11, 1, tzinfo=UTC),
            "discovered_at": datetime(2026, 11, 2, tzinfo=UTC),
        },
        None,
    )
    second = privacy_service.record_incident(
        db,
        admin,
        {
            **INCIDENT,
            "occurred_at": datetime(2026, 11, 3, tzinfo=UTC),
            "discovered_at": datetime(2026, 11, 4, tzinfo=UTC),
        },
        None,
    )

    assert [i.id for i in privacy_service.list_incidents(db)][:2] == [second.id, first.id]
