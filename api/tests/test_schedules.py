"""Front-desk day schedule and a patient's own appointments (D1 desktop and mobile)."""

import uuid
from datetime import UTC, date, datetime, time, timedelta

import pytest
from sqlalchemy.dialects.postgresql import Range

from app.models import Appointment, Patient, Service
from app.services.availability_service import today_local
from app.services.slots import local_to_utc
from tests.test_availability import make_therapist, staff_token
from tests.test_login import bearer, make_user

DESK = "/api/v1/desk/schedule"
MINE = "/api/v1/me/appointments"


def make_patient(db, name):
    user = make_user(db, f"{name.lower()}-{uuid.uuid4().hex[:6]}@example.com")
    patient = Patient(
        user_id=user.id,
        first_name=name,
        last_name="Test",
        date_of_birth=date(1990, 1, 1),
        phone="514-555-0101",
    )
    db.add(patient)
    db.commit()
    return patient


def book(db, patient, therapist, service, day, hour, status="confirmed", hold_expires_at=None):
    appointment = Appointment(
        patient_id=patient.id,
        therapist_id=therapist.id,
        service_id=service.id,
        during=Range(local_to_utc(day, time(hour)), local_to_utc(day, time(hour, 30))),
        status=status,
        created_by=patient.user_id,
        hold_expires_at=hold_expires_at,
    )
    db.add(appointment)
    db.commit()
    return appointment


@pytest.fixture
def clinic(db):
    service = Service(
        name_fr="Suivi", name_en="Follow-up", duration_min=30, price_cents=8000, deposit_cents=2000
    )
    db.add(service)
    db.commit()
    return service, make_therapist(db, "Lefebvre"), make_therapist(db, "Nguyen")


def desk_headers(db, role="front_desk", mfa=True):
    user = make_user(db, f"{role}-{uuid.uuid4().hex[:6]}@example.com", role=role)
    return bearer(staff_token(user.id, role=role, mfa=mfa))


def patient_headers(patient):
    return bearer(staff_token(patient.user_id, role="patient", mfa=False))


# --- Front desk -----------------------------------------------------------


def test_front_desk_sees_every_therapists_appointments_for_the_day(client, db, clinic):
    service, anne, sophie = clinic
    day = today_local() + timedelta(days=3)
    marie, luc = make_patient(db, "Marie"), make_patient(db, "Luc")
    book(db, marie, anne, service, day, 9)
    book(db, luc, sophie, service, day, 10)
    book(db, luc, sophie, service, day + timedelta(days=1), 9)  # another day: not shown

    body = client.get(DESK, params={"date": str(day)}, headers=desk_headers(db)).json()

    assert {t["last_name"] for t in body["therapists"]} == {"Lefebvre", "Nguyen"}
    assert [a["patient"]["first_name"] for a in body["appointments"]] == ["Marie", "Luc"]
    assert body["appointments"][0]["start_local"].startswith(f"{day}T09:00")
    assert body["appointments"][0]["patient"]["phone"] == "514-555-0101"


def test_schedule_contains_no_clinical_or_account_data(client, db, clinic):
    service, anne, _ = clinic
    day = today_local() + timedelta(days=3)
    book(db, make_patient(db, "Marie"), anne, service, day, 9)

    appointment = client.get(DESK, params={"date": str(day)}, headers=desk_headers(db)).json()[
        "appointments"
    ][0]

    assert set(appointment["patient"]) == {"id", "first_name", "last_name", "phone"}
    assert "notes" not in str(appointment).lower()


def test_expired_holds_are_not_in_the_schedule(client, db, clinic):
    service, anne, _ = clinic
    day = today_local() + timedelta(days=3)
    book(
        db,
        make_patient(db, "Gone"),
        anne,
        service,
        day,
        9,
        status="held",
        hold_expires_at=datetime.now(UTC) - timedelta(minutes=1),
    )

    body = client.get(DESK, params={"date": str(day)}, headers=desk_headers(db)).json()

    assert body["appointments"] == []


def test_admin_can_also_read_the_schedule(client, db, clinic):
    response = client.get(
        DESK, params={"date": str(today_local())}, headers=desk_headers(db, "admin")
    )

    assert response.status_code == 200


@pytest.mark.parametrize(
    ("role", "mfa"), [("front_desk", False), ("therapist", True), ("patient", False)]
)
def test_schedule_refused_without_mfa_or_for_other_roles(client, db, role, mfa):
    response = client.get(
        DESK, params={"date": str(today_local())}, headers=desk_headers(db, role, mfa)
    )

    assert response.status_code == 403


def test_schedule_needs_a_date(client, db):
    assert client.get(DESK, headers=desk_headers(db)).status_code == 422


# --- Patient's own appointments --------------------------------------------


def test_patient_sees_own_upcoming_appointments_with_therapist_and_service(client, db, clinic):
    service, anne, _ = clinic
    marie = make_patient(db, "Marie")
    soon = today_local() + timedelta(days=2)
    later = today_local() + timedelta(days=9)
    book(db, marie, anne, service, later, 10)
    book(db, marie, anne, service, soon, 9)

    body = client.get(MINE, headers=patient_headers(marie)).json()

    assert [a["start_local"][:10] for a in body] == [str(soon), str(later)]  # soonest first
    assert body[0]["therapist"]["last_name"] == "Lefebvre"
    assert body[0]["service"]["name_en"] == "Follow-up"


def test_patient_never_sees_another_patients_appointments(client, db, clinic):
    """IDOR protection (B-C3): the query is always filtered by the logged-in patient."""
    service, anne, sophie = clinic
    marie, luc = make_patient(db, "Marie"), make_patient(db, "Luc")
    day = today_local() + timedelta(days=2)
    book(db, marie, anne, service, day, 9)
    book(db, luc, sophie, service, day, 9)

    marie_sees = client.get(MINE, headers=patient_headers(marie)).json()
    luc_sees = client.get(MINE, headers=patient_headers(luc)).json()

    assert [a["therapist"]["last_name"] for a in marie_sees] == ["Lefebvre"]
    assert [a["therapist"]["last_name"] for a in luc_sees] == ["Nguyen"]


def test_past_appointments_are_not_listed(client, db, clinic):
    service, anne, _ = clinic
    marie = make_patient(db, "Marie")
    book(db, marie, anne, service, today_local() - timedelta(days=5), 9, status="completed")

    assert client.get(MINE, headers=patient_headers(marie)).json() == []


def test_staff_cannot_use_the_patient_endpoint(client, db):
    assert client.get(MINE, headers=desk_headers(db)).status_code == 403


def test_my_appointments_needs_login(client):
    assert client.get(MINE).status_code == 401
