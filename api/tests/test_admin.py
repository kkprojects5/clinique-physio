"""Administration (B-ADM-01 services and staff, B-ADM-03 audit log viewer)."""

import re
import uuid
from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import select

from app.core.security import hash_refresh_token
from app.models import AuditLog, PasswordResetToken, RefreshToken, Service, Therapist, User
from app.services import admin_service
from app.services.availability_service import find_slots, list_therapists, today_local
from tests.test_booking import clinic  # noqa: F401  (fixture)
from tests.test_clinical import as_staff
from tests.test_login import make_user

ADMIN = "/api/v1/admin"


@pytest.fixture
def admin(db):
    return make_user(db, f"admin-{uuid.uuid4().hex[:6]}@example.com", role="admin")


@pytest.fixture
def headers(admin):
    return as_staff(admin, role="admin", app="web")


@pytest.fixture
def outbox(monkeypatch):
    sent = []
    monkeypatch.setattr(admin_service, "send_email", lambda to, subject, body: sent.append(body))
    return sent


def logged(db, action, resource_type):
    return db.scalars(
        select(AuditLog).where(AuditLog.action == action, AuditLog.resource_type == resource_type)
    ).all()


# --- Access -------------------------------------------------------------------------------------


@pytest.mark.parametrize("role", ["therapist", "front_desk", "patient"])
def test_only_administrators_use_the_admin_pages(client, db, role):
    user = make_user(db, f"{role}-{uuid.uuid4().hex[:6]}@example.com", role=role)

    for path in ("/services", "/staff", "/audit"):
        assert client.get(ADMIN + path, headers=as_staff(user, role=role)).status_code == 403


def test_admin_needs_the_two_factor_session(client, admin):
    from tests.test_availability import staff_token
    from tests.test_login import bearer

    no_mfa = bearer(staff_token(admin.id, role="admin", mfa=False))

    assert client.get(ADMIN + "/services", headers=no_mfa).status_code == 403
    assert client.get(ADMIN + "/services").status_code == 401


# --- Services -----------------------------------------------------------------------------------


NEW_SERVICE = {
    "name_fr": "Rééducation vestibulaire",
    "name_en": "Vestibular rehabilitation",
    "duration_min": 45,
    "price_cents": 10500,
    "deposit_cents": 2500,
}


def test_create_a_service_with_its_therapists(client, db, headers, clinic):  # noqa: F811
    body = {**NEW_SERVICE, "therapist_ids": [str(clinic["anne"].id)]}

    response = client.post(ADMIN + "/services", json=body, headers=headers)

    assert response.status_code == 201
    created = response.json()
    assert created["is_active"] is True
    assert created["therapist_ids"] == [str(clinic["anne"].id)]
    assert len(logged(db, "create", "service")) == 1
    public = client.get("/api/v1/services").json()
    assert "Rééducation vestibulaire" in [s["name_fr"] for s in public]


@pytest.mark.parametrize(
    "change",
    [
        {"deposit_cents": 20000},  # more than the price
        {"duration_min": 50},  # not 30, 45 or 60
        {"price_cents": -1},
        {"name_fr": "x"},
    ],
)
def test_invalid_service_values_are_refused(client, headers, change):
    response = client.post(ADMIN + "/services", json={**NEW_SERVICE, **change}, headers=headers)

    assert response.status_code == 422


def test_unknown_therapist_is_refused(client, db, headers):
    body = {**NEW_SERVICE, "therapist_ids": [str(uuid.uuid4())]}

    assert client.post(ADMIN + "/services", json=body, headers=headers).status_code == 422
    assert db.scalar(select(Service).where(Service.name_en == NEW_SERVICE["name_en"])) is None


def test_change_price_and_therapists(client, db, headers, clinic):  # noqa: F811
    treatment, sophie = clinic["treatment"], clinic["sophie"]

    response = client.patch(
        f"{ADMIN}/services/{treatment.id}",
        json={"price_cents": 8500, "therapist_ids": [str(sophie.id)]},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["price_cents"] == 8500
    assert response.json()["therapist_ids"] == [str(sophie.id)]
    assert response.json()["name_fr"] == "Traitement"  # unchanged


def test_deposit_cannot_exceed_a_lowered_price(client, headers, clinic):  # noqa: F811
    response = client.patch(
        f"{ADMIN}/services/{clinic['treatment'].id}", json={"price_cents": 1000}, headers=headers
    )

    assert response.status_code == 422


def test_deactivated_service_disappears_from_booking(client, db, headers, clinic):  # noqa: F811
    treatment = clinic["treatment"]

    response = client.patch(
        f"{ADMIN}/services/{treatment.id}", json={"is_active": False}, headers=headers
    )

    assert response.status_code == 200
    public = [s["id"] for s in client.get("/api/v1/services").json()]
    assert str(treatment.id) not in public
    assert str(treatment.id) in [
        s["id"] for s in client.get(ADMIN + "/services", headers=headers).json()
    ]
    assert len(logged(db, "deactivate", "service")) == 1


def test_a_required_field_cannot_be_emptied(client, headers, clinic):  # noqa: F811
    response = client.patch(
        f"{ADMIN}/services/{clinic['treatment'].id}", json={"name_fr": None}, headers=headers
    )

    assert response.status_code == 422


# --- Staff --------------------------------------------------------------------------------------


NEW_THERAPIST = {
    "email": "Julie.Roy@Example.com",
    "role": "therapist",
    "therapist": {"first_name": "Julie", "last_name": "Roy", "licence_number": "PT-99001"},
}


def test_new_therapist_gets_an_invitation_never_a_password(client, db, headers, outbox):
    response = client.post(ADMIN + "/staff", json=NEW_THERAPIST, headers=headers)

    assert response.status_code == 201
    staff = response.json()
    assert staff["email"] == "julie.roy@example.com"
    assert staff["mfa_ready"] is False
    assert "password" not in str(staff).lower()
    user = db.get(User, uuid.UUID(staff["id"]))
    assert db.scalar(select(Therapist).where(Therapist.user_id == user.id)).last_name == "Roy"
    # The invitation link works once for 72 hours and only its hash is stored.
    link = re.search(r"token=(\S+)", outbox[0])[1]
    token = db.scalar(
        select(PasswordResetToken).where(PasswordResetToken.token_hash == hash_refresh_token(link))
    )
    assert token.expires_at - datetime.now(UTC) > timedelta(hours=71)
    assert len(logged(db, "create", "user")) == 1


def test_invited_staff_chooses_a_password_then_still_needs_mfa(client, headers, outbox):
    client.post(ADMIN + "/staff", json=NEW_THERAPIST, headers=headers)
    token = re.search(r"token=(\S+)", outbox[0])[1]

    reset = client.post(
        "/api/v1/auth/password/reset", json={"token": token, "new_password": "Une-phrase-longue-42"}
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "julie.roy@example.com", "password": "Une-phrase-longue-42"},
    )

    assert reset.status_code == 200
    assert login.status_code == 200
    assert login.json()["mfa_setup_required"] is True
    assert "access_token" not in login.json()


def test_front_desk_account_needs_no_licence(client, headers, outbox):
    body = {"email": "accueil3@example.com", "role": "front_desk", "language": "en"}

    response = client.post(ADMIN + "/staff", json=body, headers=headers)

    assert response.status_code == 201
    assert response.json()["therapist_id"] is None
    assert "A front desk account" in outbox[0]


@pytest.mark.parametrize(
    "body",
    [
        {**NEW_THERAPIST, "role": "admin"},  # no new administrators through the API
        {**NEW_THERAPIST, "role": "patient"},
        {"email": "a@example.com", "role": "therapist"},  # therapist without a name or licence
        {**NEW_THERAPIST, "email": "not-an-email"},
    ],
)
def test_invalid_staff_accounts_are_refused(client, headers, body):
    assert client.post(ADMIN + "/staff", json=body, headers=headers).status_code == 422


def test_service_layer_also_refuses_new_administrators(db, admin):
    """Second line of defence behind the API schema."""
    with pytest.raises(admin_service.AdminError):
        admin_service.create_staff(db, admin, "x@example.com", "admin", "fr", None, None)


def test_email_and_licence_must_be_unique(client, headers, outbox):
    client.post(ADMIN + "/staff", json=NEW_THERAPIST, headers=headers)
    same_licence = {**NEW_THERAPIST, "email": "autre@example.com"}

    assert client.post(ADMIN + "/staff", json=NEW_THERAPIST, headers=headers).status_code == 409
    assert client.post(ADMIN + "/staff", json=same_licence, headers=headers).status_code == 409


def test_deactivating_closes_sessions_and_hides_the_therapist(client, db, headers, clinic):  # noqa: F811
    anne = clinic["anne"]
    db.add(
        RefreshToken(
            user_id=anne.user_id,
            token_hash="x" * 64,
            expires_at=datetime.now(UTC) + timedelta(days=1),
        )
    )
    db.commit()

    response = client.patch(
        f"{ADMIN}/staff/{anne.user_id}", json={"is_active": False}, headers=headers
    )

    assert response.status_code == 200
    assert response.json()["is_active"] is False
    token = db.scalar(select(RefreshToken).where(RefreshToken.user_id == anne.user_id))
    assert token.revoked_at is not None
    # Her old access token no longer works, she leaves the team page and offers no slot.
    assert client.get("/api/v1/therapist/me", headers=as_staff(anne)).status_code == 401
    assert anne.id not in [t.id for t, _ in list_therapists(db)]
    monday = today_local() + timedelta(days=(7 - today_local().weekday()) % 7 or 7)
    slots = find_slots(db, clinic["treatment"].id, None, monday, monday)
    assert slots and {s.therapist_id for s in slots} == {clinic["sophie"].id}
    assert len(logged(db, "deactivate", "user")) == 1


def test_reactivating_brings_the_account_back(client, db, headers, clinic):  # noqa: F811
    anne = clinic["anne"]
    client.patch(f"{ADMIN}/staff/{anne.user_id}", json={"is_active": False}, headers=headers)

    response = client.patch(
        f"{ADMIN}/staff/{anne.user_id}", json={"is_active": True}, headers=headers
    )

    assert response.json()["is_active"] is True
    assert anne.id in [t.id for t, _ in list_therapists(db)]


def test_admin_cannot_deactivate_itself_or_another_admin(client, db, admin, headers):
    other = make_user(db, f"admin2-{uuid.uuid4().hex[:6]}@example.com", role="admin")

    me = client.patch(f"{ADMIN}/staff/{admin.id}", json={"is_active": False}, headers=headers)
    them = client.patch(f"{ADMIN}/staff/{other.id}", json={"is_active": False}, headers=headers)

    assert me.status_code == 409
    assert me.json()["detail"] == "You cannot deactivate your own account."
    assert them.status_code == 409
    assert them.json()["detail"] == "Administrator accounts are managed by the clinic owner."


def test_patients_are_not_managed_as_staff(client, db, headers):
    patient = make_user(db, f"p-{uuid.uuid4().hex[:6]}@example.com")

    response = client.patch(
        f"{ADMIN}/staff/{patient.id}", json={"is_active": False}, headers=headers
    )

    assert response.status_code == 404
    assert patient.email not in [
        s["email"] for s in client.get(ADMIN + "/staff", headers=headers).json()
    ]


def test_resent_invitation_replaces_the_old_link(client, db, headers, outbox):
    staff_id = client.post(ADMIN + "/staff", json=NEW_THERAPIST, headers=headers).json()["id"]

    response = client.post(f"{ADMIN}/staff/{staff_id}/invitation", headers=headers)

    assert response.status_code == 204
    first, second = (re.search(r"token=(\S+)", body)[1] for body in outbox)
    old = client.post(
        "/api/v1/auth/password/reset", json={"token": first, "new_password": "Une-phrase-longue-42"}
    )
    assert old.status_code == 400
    assert first != second


def test_staff_list_shows_future_appointments_to_move(client, db, headers, clinic):  # noqa: F811
    staff = client.get(ADMIN + "/staff", headers=headers).json()

    anne = next(s for s in staff if s["therapist_id"] == str(clinic["anne"].id))
    assert anne["first_name"] and anne["licence_number"]
    assert anne["future_appointments"] == 0


# --- Audit log ----------------------------------------------------------------------------------


def add_entries(db, actor, count, **fields):
    for _ in range(count):
        db.add(AuditLog(actor_id=actor.id, action="read", resource_type="clinical_note", **fields))
    db.commit()


def test_audit_log_newest_first_with_who_did_it(client, db, admin, headers):
    therapist = make_user(db, f"t-{uuid.uuid4().hex[:6]}@example.com", role="therapist")
    add_entries(db, therapist, 2)

    page = client.get(ADMIN + "/audit", headers=headers).json()

    entries = page["entries"]
    assert [e["id"] for e in entries] == sorted((e["id"] for e in entries), reverse=True)
    assert entries[0]["actor_email"] == therapist.email
    assert entries[0]["actor_role"] == "therapist"
    assert page["next_before_id"] is None


def test_audit_log_pages(client, db, admin, headers):
    add_entries(db, admin, 5)

    first = client.get(ADMIN + "/audit?limit=2", headers=headers).json()
    second = client.get(
        f"{ADMIN}/audit?limit=2&before_id={first['next_before_id']}", headers=headers
    ).json()

    assert len(first["entries"]) == 2 and len(second["entries"]) == 2
    assert first["entries"][-1]["id"] > second["entries"][0]["id"]


def test_audit_log_filters(client, db, admin, headers):
    therapist = make_user(db, f"t-{uuid.uuid4().hex[:6]}@example.com", role="therapist")
    add_entries(db, therapist, 1)
    add_entries(db, admin, 1)

    by_actor = client.get(f"{ADMIN}/audit?actor_email={therapist.email}", headers=headers).json()
    by_action = client.get(f"{ADMIN}/audit?action=access_denied", headers=headers).json()
    tomorrow = (date.today() + timedelta(days=2)).isoformat()
    future = client.get(f"{ADMIN}/audit?date_from={tomorrow}", headers=headers).json()

    assert {e["actor_email"] for e in by_actor["entries"]} == {therapist.email}
    assert by_action["entries"] == []
    assert future["entries"] == []


def test_reading_the_audit_log_is_itself_logged(client, db, headers):
    client.get(ADMIN + "/audit", headers=headers)

    assert len(logged(db, "read", "audit_log")) == 1


def test_audit_log_page_size_is_limited(client, headers):
    assert client.get(ADMIN + "/audit?limit=500", headers=headers).status_code == 422


def make_patients(db, count):
    from app.models import Patient

    patients = []
    for i in range(count):
        user = make_user(db, f"pat{i}-{uuid.uuid4().hex[:6]}@example.com")
        patient = Patient(
            user_id=user.id,
            first_name=f"P{i}",
            last_name="Test",
            date_of_birth=date(1980, 1, 1),
            phone="514-555-0199",
        )
        db.add(patient)
        patients.append(patient)
    db.commit()
    return patients


def test_many_patient_files_in_one_hour_are_highlighted(client, db, headers):
    busy = make_user(db, f"busy-{uuid.uuid4().hex[:6]}@example.com", role="therapist")
    calm = make_user(db, f"calm-{uuid.uuid4().hex[:6]}@example.com", role="therapist")
    patients = make_patients(db, admin_service.UNUSUAL_PATIENTS_PER_HOUR + 1)
    for p in patients:
        add_entries(db, busy, 1, patient_id=p.id)
    for p in patients[:3]:
        add_entries(db, calm, 1, patient_id=p.id)

    entries = client.get(ADMIN + "/audit?limit=100", headers=headers).json()["entries"]

    by_actor = {}
    for e in entries:
        by_actor.setdefault(e["actor_email"], set()).add(e["unusual"])
    assert by_actor[busy.email] == {True}
    assert by_actor[calm.email] == {False}


def test_refused_access_is_highlighted(client, db, headers):
    therapist = make_user(db, f"t-{uuid.uuid4().hex[:6]}@example.com", role="therapist")
    db.add(AuditLog(actor_id=therapist.id, action="access_denied", resource_type="patient"))
    db.commit()

    entries = client.get(f"{ADMIN}/audit?actor_email={therapist.email}", headers=headers).json()

    assert entries["entries"][0]["unusual"] is True


def test_filter_by_patient(client, db, headers):
    therapist = make_user(db, f"t-{uuid.uuid4().hex[:6]}@example.com", role="therapist")
    first, second = make_patients(db, 2)
    add_entries(db, therapist, 1, patient_id=first.id)
    add_entries(db, therapist, 1, patient_id=second.id)

    entries = client.get(f"{ADMIN}/audit?patient_id={first.id}", headers=headers).json()["entries"]

    assert {e["patient_name"] for e in entries} == {"P0 Test"}
