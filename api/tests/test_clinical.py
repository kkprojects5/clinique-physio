"""Patient files and SOAP notes: care relationship, encryption, signature, audit
(B-AUTH-05, B-CLN-01 to 05)."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import Range
from sqlalchemy.exc import DBAPIError

from app.models import Appointment, AuditLog, ClinicalNote, Service, User
from tests.test_availability import make_therapist, staff_token
from tests.test_login import bearer, make_user
from tests.test_schedules import make_patient, patient_headers

BASE = "/api/v1/therapist"
SOAP = {
    "subjective": "Douleur au genou droit depuis 2 semaines, 6/10 à la marche.",
    "objective": "Flexion limitée à 110°, oedème léger.",
    "assessment": "Tendinopathie rotulienne probable.",
    "plan": "Exercices excentriques, revoir dans 1 semaine.",
}


@pytest.fixture
def clinic(db):
    service = Service(
        name_fr="Suivi", name_en="Follow-up", duration_min=30, price_cents=8000, deposit_cents=2000
    )
    db.add(service)
    db.commit()
    anne, sophie, paul = (make_therapist(db, n) for n in ("Lefebvre", "Nguyen", "Roy"))
    marie = make_patient(db, "Marie")
    return {"service": service, "anne": anne, "sophie": sophie, "paul": paul, "marie": marie}


def visit(db, clinic, therapist, patient, hours_from_now=-2, status="confirmed"):
    start = datetime.now(UTC).replace(microsecond=0) + timedelta(hours=hours_from_now)
    appointment = Appointment(
        patient_id=patient.id,
        therapist_id=therapist.id,
        service_id=clinic["service"].id,
        during=Range(start, start + timedelta(minutes=30)),
        status=status,
        created_by=patient.user_id,
    )
    db.add(appointment)
    db.commit()
    return appointment


def as_staff(therapist_or_user, role="therapist", app=None):
    user_id = getattr(therapist_or_user, "user_id", None) or therapist_or_user.id
    headers = bearer(staff_token(user_id, role=role))
    if app:
        headers["X-Client-App"] = app
    return headers


def audits(db, **filters):
    query = select(AuditLog).order_by(AuditLog.id)
    for key, value in filters.items():
        query = query.where(getattr(AuditLog, key) == value)
    return db.scalars(query).all()


def write_note(client, therapist, appointment, content=SOAP):
    return client.post(
        f"{BASE}/appointments/{appointment.id}/notes", json=content, headers=as_staff(therapist)
    )


# --- Care relationship (B-AUTH-05, B-CLN-01) ----------------------------------------


def test_a_therapist_lists_only_the_patients_they_treat(client, db, clinic):
    visit(db, clinic, clinic["anne"], clinic["marie"])
    luc = make_patient(db, "Luc")
    visit(db, clinic, clinic["sophie"], luc)

    body = client.get(f"{BASE}/patients", headers=as_staff(clinic["anne"])).json()

    assert [p["first_name"] for p in body] == ["Marie"]


def test_cancelled_or_expired_appointments_give_no_access(client, db, clinic):
    visit(db, clinic, clinic["anne"], clinic["marie"], status="cancelled_by_patient")
    visit(db, clinic, clinic["anne"], clinic["marie"], status="expired")

    response = client.get(f"{BASE}/patients/{clinic['marie'].id}", headers=as_staff(clinic["anne"]))

    assert response.status_code == 404


def test_patient_file_with_history_and_audit(client, db, clinic):
    visit(db, clinic, clinic["anne"], clinic["marie"])

    response = client.get(
        f"{BASE}/patients/{clinic['marie'].id}", headers=as_staff(clinic["anne"], app="web")
    )

    assert response.status_code == 200
    assert response.json()["first_name"] == "Marie"
    assert len(response.json()["history"]) == 1
    [entry] = audits(db, patient_id=clinic["marie"].id)
    assert (entry.actor_id, entry.action, entry.resource_type, entry.client_app) == (
        clinic["anne"].user_id,
        "read",
        "patient",
        "web",
    )


def test_therapist_without_care_relationship_gets_404_and_is_audited(client, db, clinic):
    visit(db, clinic, clinic["anne"], clinic["marie"])

    response = client.get(f"{BASE}/patients/{clinic['marie'].id}", headers=as_staff(clinic["paul"]))

    assert response.status_code == 404
    [entry] = audits(db, actor_id=clinic["paul"].user_id)
    assert (entry.action, entry.patient_id) == ("access_denied", clinic["marie"].id)


def test_unknown_patient_looks_the_same_as_a_refused_one(client, db, clinic):
    response = client.get(f"{BASE}/patients/{uuid.uuid4()}", headers=as_staff(clinic["paul"]))

    assert response.status_code == 404
    assert response.json()["detail"] == "Not found."


# --- Writing notes (B-CLN-02) --------------------------------------------------------


def test_write_a_note_after_the_appointment(client, db, clinic):
    appointment = visit(db, clinic, clinic["anne"], clinic["marie"])

    response = write_note(client, clinic["anne"], appointment)

    assert response.status_code == 201
    body = response.json()
    assert body["content"] == SOAP
    assert body["signed_at"] is None
    assert body["patient_id"] == str(clinic["marie"].id)
    assert [a.action for a in audits(db, resource_type="clinical_note")] == ["create"]


def test_note_content_is_encrypted_in_the_database(client, db, clinic):
    appointment = visit(db, clinic, clinic["anne"], clinic["marie"])
    write_note(client, clinic["anne"], appointment)

    raw = db.execute(text("SELECT content_encrypted FROM clinical_notes")).scalar_one()

    assert b"genou" not in bytes(raw)
    assert b"Tendinopathie" not in bytes(raw)


def test_no_note_before_the_appointment(client, db, clinic):
    future = visit(db, clinic, clinic["anne"], clinic["marie"], hours_from_now=24)

    assert write_note(client, clinic["anne"], future).status_code == 409


def test_only_the_appointments_therapist_writes_its_note(client, db, clinic):
    appointment = visit(db, clinic, clinic["anne"], clinic["marie"])
    visit(db, clinic, clinic["sophie"], clinic["marie"])  # Sophie also treats Marie

    response = write_note(client, clinic["sophie"], appointment)

    assert response.status_code == 404
    assert audits(db, actor_id=clinic["sophie"].user_id)[0].action == "access_denied"


def test_one_original_note_per_appointment(client, db, clinic):
    appointment = visit(db, clinic, clinic["anne"], clinic["marie"])
    write_note(client, clinic["anne"], appointment)

    assert write_note(client, clinic["anne"], appointment).status_code == 409


def test_empty_note_is_refused(client, db, clinic):
    appointment = visit(db, clinic, clinic["anne"], clinic["marie"])
    empty = {"subjective": " ", "objective": "", "assessment": "", "plan": ""}

    assert write_note(client, clinic["anne"], appointment, empty).status_code == 422


# --- Reading notes (B-AUTH-05, B-CLN-04) ---------------------------------------------


def test_another_therapist_treating_the_patient_can_read_and_it_is_audited(client, db, clinic):
    appointment = visit(db, clinic, clinic["anne"], clinic["marie"])
    note = write_note(client, clinic["anne"], appointment).json()
    visit(db, clinic, clinic["sophie"], clinic["marie"])

    response = client.get(
        f"{BASE}/notes/{note['id']}", headers=as_staff(clinic["sophie"], app="desktop")
    )

    assert response.status_code == 200
    assert response.json()["content"]["plan"] == SOAP["plan"]
    entry = audits(db, actor_id=clinic["sophie"].user_id)[-1]
    assert (entry.action, entry.resource_id, entry.client_app) == (
        "read",
        uuid.UUID(note["id"]),
        "desktop",
    )


def test_therapist_without_care_relationship_cannot_read_a_note(client, db, clinic):
    appointment = visit(db, clinic, clinic["anne"], clinic["marie"])
    note = write_note(client, clinic["anne"], appointment).json()

    response = client.get(f"{BASE}/notes/{note['id']}", headers=as_staff(clinic["paul"]))
    listing = client.get(
        f"{BASE}/patients/{clinic['marie'].id}/notes", headers=as_staff(clinic["paul"])
    )

    assert response.status_code == listing.status_code == 404
    assert "Tendinopathie" not in response.text + listing.text
    assert [a.action for a in audits(db, actor_id=clinic["paul"].user_id)] == [
        "access_denied",
        "access_denied",
    ]


def test_listing_a_patients_notes_audits_each_note(client, db, clinic):
    first = visit(db, clinic, clinic["anne"], clinic["marie"], hours_from_now=-48)
    second = visit(db, clinic, clinic["anne"], clinic["marie"])
    write_note(client, clinic["anne"], first)
    write_note(client, clinic["anne"], second)

    response = client.get(
        f"{BASE}/patients/{clinic['marie'].id}/notes", headers=as_staff(clinic["anne"])
    )

    assert len(response.json()) == 2
    reads = [a for a in audits(db, resource_type="clinical_note") if a.action == "read"]
    assert len(reads) == 2


@pytest.mark.parametrize("role", ["front_desk", "admin"])
def test_front_desk_and_admin_never_reach_clinical_notes(client, db, clinic, role):
    appointment = visit(db, clinic, clinic["anne"], clinic["marie"])
    note = write_note(client, clinic["anne"], appointment).json()
    staff = make_user(db, f"{role}-{uuid.uuid4().hex[:6]}@example.com", role=role)
    headers = as_staff(staff, role=role)

    for url in (
        f"{BASE}/notes/{note['id']}",
        f"{BASE}/patients/{clinic['marie'].id}",
        f"{BASE}/patients/{clinic['marie'].id}/notes",
        f"{BASE}/patients",
    ):
        response = client.get(url, headers=headers)
        assert response.status_code == 403, url
        assert "Tendinopathie" not in response.text


def test_patients_and_anonymous_users_are_refused(client, db, clinic):
    appointment = visit(db, clinic, clinic["anne"], clinic["marie"])
    note = write_note(client, clinic["anne"], appointment).json()

    assert client.get(f"{BASE}/notes/{note['id']}").status_code == 401
    own = client.get(f"{BASE}/notes/{note['id']}", headers=patient_headers(clinic["marie"]))
    assert own.status_code == 403


def test_staff_without_mfa_are_refused(client, db, clinic):
    headers = bearer(staff_token(clinic["anne"].user_id, mfa=False))

    assert client.get(f"{BASE}/patients", headers=headers).status_code == 403


# --- Drafts, signature, amendments (B-CLN-03) ---------------------------------------


def test_author_edits_a_draft_then_signs_it(client, db, clinic):
    appointment = visit(db, clinic, clinic["anne"], clinic["marie"])
    note = write_note(client, clinic["anne"], appointment).json()
    changed = {**SOAP, "plan": "Exercices excentriques 3x/semaine."}

    edited = client.put(
        f"{BASE}/notes/{note['id']}", json=changed, headers=as_staff(clinic["anne"])
    )
    signed = client.post(f"{BASE}/notes/{note['id']}/sign", headers=as_staff(clinic["anne"]))

    assert edited.json()["version"] == 2
    assert edited.json()["content"]["plan"] == changed["plan"]
    assert signed.json()["signed_at"] is not None
    actions = [a.action for a in audits(db, resource_type="clinical_note")]
    assert actions == ["create", "update", "sign"]


def test_a_signed_note_can_no_longer_be_changed(client, db, clinic):
    appointment = visit(db, clinic, clinic["anne"], clinic["marie"])
    note = write_note(client, clinic["anne"], appointment).json()
    client.post(f"{BASE}/notes/{note['id']}/sign", headers=as_staff(clinic["anne"]))

    response = client.put(f"{BASE}/notes/{note['id']}", json=SOAP, headers=as_staff(clinic["anne"]))

    assert response.status_code == 409
    assert "Add an amendment" in response.json()["detail"]


def test_only_the_author_edits_a_draft(client, db, clinic):
    appointment = visit(db, clinic, clinic["anne"], clinic["marie"])
    note = write_note(client, clinic["anne"], appointment).json()
    visit(db, clinic, clinic["sophie"], clinic["marie"])

    response = client.put(
        f"{BASE}/notes/{note['id']}", json=SOAP, headers=as_staff(clinic["sophie"])
    )

    assert response.status_code == 409


def test_amendment_keeps_the_original(client, db, clinic):
    appointment = visit(db, clinic, clinic["anne"], clinic["marie"])
    note = write_note(client, clinic["anne"], appointment).json()
    assert (
        client.post(
            f"{BASE}/notes/{note['id']}/amendments", json=SOAP, headers=as_staff(clinic["anne"])
        ).status_code
        == 409
    )  # drafts are edited, not amended
    client.post(f"{BASE}/notes/{note['id']}/sign", headers=as_staff(clinic["anne"]))
    correction = {**SOAP, "assessment": "Tendinopathie rotulienne confirmée."}

    response = client.post(
        f"{BASE}/notes/{note['id']}/amendments", json=correction, headers=as_staff(clinic["anne"])
    )

    assert response.status_code == 201
    assert response.json()["amends_note_id"] == note["id"]
    assert response.json()["signed_at"] is not None
    original = client.get(f"{BASE}/notes/{note['id']}", headers=as_staff(clinic["anne"])).json()
    assert original["content"]["assessment"] == SOAP["assessment"]


# --- Database protections -------------------------------------------------------------


def _refused_by_database(db, sql, **params):
    savepoint = db.begin_nested()
    with pytest.raises(DBAPIError):
        db.execute(text(sql), params)
    savepoint.rollback()


def test_database_refuses_changing_a_signed_note_or_deleting_any_note(client, db, clinic):
    appointment = visit(db, clinic, clinic["anne"], clinic["marie"])
    note = write_note(client, clinic["anne"], appointment).json()
    client.post(f"{BASE}/notes/{note['id']}/sign", headers=as_staff(clinic["anne"]))

    _refused_by_database(db, "UPDATE clinical_notes SET version = 99 WHERE id = :id", id=note["id"])
    _refused_by_database(db, "DELETE FROM clinical_notes WHERE id = :id", id=note["id"])
    assert db.get(ClinicalNote, uuid.UUID(note["id"])).version == 1


def test_database_refuses_changing_or_deleting_audit_entries(client, db, clinic):
    visit(db, clinic, clinic["anne"], clinic["marie"])
    client.get(f"{BASE}/patients/{clinic['marie'].id}", headers=as_staff(clinic["anne"]))

    _refused_by_database(db, "UPDATE audit_logs SET action = 'nothing'")
    _refused_by_database(db, "DELETE FROM audit_logs")
    assert len(audits(db)) == 1


def test_unknown_client_app_is_recorded_as_other(client, db, clinic):
    visit(db, clinic, clinic["anne"], clinic["marie"])
    headers = as_staff(clinic["anne"], app="<script>")

    client.get(f"{BASE}/patients/{clinic['marie'].id}", headers=headers)

    assert audits(db)[0].client_app == "other"
    assert db.get(User, clinic["anne"].user_id) is not None


def test_therapist_me_and_history_say_whose_appointment_it_is(client, db, clinic):
    visit(db, clinic, clinic["anne"], clinic["marie"])
    visit(db, clinic, clinic["sophie"], clinic["marie"], hours_from_now=-30)

    me = client.get(f"{BASE}/me", headers=as_staff(clinic["anne"])).json()
    history = client.get(
        f"{BASE}/patients/{clinic['marie'].id}", headers=as_staff(clinic["anne"])
    ).json()["history"]

    assert me == {
        "id": str(clinic["anne"].id),
        "first_name": clinic["anne"].first_name,
        "last_name": "Lefebvre",
    }
    assert {h["therapist_id"] for h in history} == {
        str(clinic["anne"].id),
        str(clinic["sophie"].id),
    }
