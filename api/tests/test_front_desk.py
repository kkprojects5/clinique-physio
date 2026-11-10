"""Front desk: find a patient, book/move/cancel by phone, check-in, no-show (B-FRD-02, 03)."""

import uuid
from datetime import UTC, date, datetime, time, timedelta

import pytest
from sqlalchemy import select

from app.main import app
from app.models import Appointment, AppointmentStatusHistory, Patient, User
from app.services import front_desk_service
from app.services.availability_service import today_local
from app.services.slots import local_to_utc
from app.services.stripe_gateway import get_gateway
from tests.test_booking import at, clinic, place  # noqa: F401  (fixture)
from tests.test_clinical import as_staff
from tests.test_login import make_user
from tests.test_payments import FakeStripe
from tests.test_schedules import make_patient, patient_headers

DESK = "/api/v1/desk"


@pytest.fixture
def desk(db):
    return make_user(db, f"accueil-{uuid.uuid4().hex[:6]}@example.com", role="front_desk")


@pytest.fixture
def marie(db):
    user = make_user(db, f"marie-{uuid.uuid4().hex[:6]}@example.com")
    patient = Patient(
        user_id=user.id,
        first_name="Marie",
        last_name="Tremblay",
        date_of_birth=date(1990, 5, 12),
        phone="514-555-0123",
    )
    db.add(patient)
    db.commit()
    return patient


def headers(desk):
    return as_staff(desk, role="front_desk", app="desktop")


def last_history(db, appointment_id):
    return db.scalars(
        select(AppointmentStatusHistory)
        .where(AppointmentStatusHistory.appointment_id == appointment_id)
        .order_by(AppointmentStatusHistory.changed_at.desc())
    ).first()


# --- Find a patient --------------------------------------------------------------


@pytest.mark.parametrize(
    "query", ["trem", "Marie Tremblay", "tremblay marie", "0123", "514 555 0123", "1990-05-12"]
)
def test_find_a_patient_by_name_phone_or_birth_date(client, desk, marie, query):
    response = client.get(f"{DESK}/patients", params={"q": query}, headers=headers(desk))

    assert response.status_code == 200
    assert [p["last_name"] for p in response.json()] == ["Tremblay"]
    assert set(response.json()[0]) == {"id", "first_name", "last_name", "date_of_birth", "phone"}


@pytest.mark.parametrize("query", ["%%", "__", "%_%", "zzzz", "1999-01-01", "2026-02-31"])
def test_wildcards_and_unknown_values_find_nobody(client, db, desk, marie, query):
    make_patient(db, "Luc")

    response = client.get(f"{DESK}/patients", params={"q": query}, headers=headers(desk))

    assert response.status_code == 200
    assert response.json() == []


def test_search_needs_two_characters(client, desk):
    assert (
        client.get(f"{DESK}/patients", params={"q": "a"}, headers=headers(desk)).status_code == 422
    )


def test_search_returns_at_most_20(client, db, desk):
    for _ in range(25):
        make_patient(db, "Gagnon")

    response = client.get(f"{DESK}/patients", params={"q": "gagnon"}, headers=headers(desk))

    assert len(response.json()) == front_desk_service.SEARCH_LIMIT == 20


@pytest.mark.parametrize("role", ["therapist", "patient"])
def test_only_front_desk_and_admin_use_the_desk(client, db, marie, role):
    other = make_user(db, f"{role}-{uuid.uuid4().hex[:6]}@example.com", role=role)
    staff = as_staff(other, role=role) if role != "patient" else patient_headers(marie)

    assert client.get(f"{DESK}/patients", params={"q": "marie"}, headers=staff).status_code == 403


def test_admin_can_use_the_desk(client, db, marie):
    admin = make_user(db, f"admin-{uuid.uuid4().hex[:6]}@example.com", role="admin")

    response = client.get(
        f"{DESK}/patients", params={"q": "marie"}, headers=as_staff(admin, role="admin")
    )

    assert response.status_code == 200


# --- Book by phone ---------------------------------------------------------------


def book(client, desk, patient, service, start, therapist=None):
    body = {
        "patient_id": str(patient.id),
        "service_id": str(service.id),
        "start": start.isoformat(),
    }
    if therapist is not None:
        body["therapist_id"] = str(therapist.id)
    return client.post(f"{DESK}/appointments", json=body, headers=headers(desk))


def test_book_by_phone_is_confirmed_at_once(client, db, desk, marie, clinic):
    response = book(client, desk, marie, clinic["evaluation"], at(8), clinic["anne"])

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "confirmed"
    assert body["patient"]["last_name"] == "Tremblay"
    appointment = db.get(Appointment, uuid.UUID(body["id"]))
    assert appointment.hold_expires_at is None
    assert appointment.created_by == desk.id
    history = last_history(db, appointment.id)
    assert (history.to_status, history.changed_by, history.reason) == (
        "confirmed",
        desk.id,
        "booked by phone (front desk)",
    )


def test_phone_booking_follows_the_same_rules_as_online(client, db, desk, marie, clinic):
    luc = make_patient(db, "Luc")
    place(db, luc, clinic["anne"], clinic["evaluation"], at(8))

    taken = book(client, desk, marie, clinic["evaluation"], at(8), clinic["anne"])
    not_offered = book(client, desk, marie, clinic["evaluation"], at(13), clinic["anne"])
    no_evaluation = book(client, desk, marie, clinic["treatment"], at(10), clinic["anne"])
    unknown = client.post(
        f"{DESK}/appointments",
        json={
            "patient_id": str(uuid.uuid4()),
            "service_id": str(clinic["evaluation"].id),
            "start": at(9).isoformat(),
        },
        headers=headers(desk),
    )

    assert taken.status_code == not_offered.status_code == no_evaluation.status_code == 409
    assert "initial evaluation" in no_evaluation.json()["detail"]
    assert unknown.status_code == 404


def test_first_available_by_phone(client, db, desk, marie, clinic):
    place(db, make_patient(db, "Luc"), clinic["anne"], clinic["evaluation"], at(8))

    response = book(client, desk, marie, clinic["evaluation"], at(8))

    assert response.status_code == 201
    assert response.json()["therapist_id"] == str(clinic["sophie"].id)


# --- Cancel and move by phone ------------------------------------------------------


@pytest.fixture
def fake_stripe():
    fake = FakeStripe()
    app.dependency_overrides[get_gateway] = lambda: fake
    yield fake
    app.dependency_overrides.pop(get_gateway, None)


def test_cancel_by_phone_follows_the_24_hour_rule(client, db, desk, marie, clinic, fake_stripe):
    appointment = place(db, marie, clinic["anne"], clinic["evaluation"], at(8))

    response = client.post(f"{DESK}/appointments/{appointment.id}/cancel", headers=headers(desk))

    assert response.status_code == 200
    assert response.json()["deposit_refunded"] is True
    history = last_history(db, appointment.id)
    assert (history.to_status, history.changed_by, history.reason) == (
        "cancelled_by_patient",
        desk.id,
        "by phone: deposit refunded",
    )


def test_desk_can_move_an_appointment_even_less_than_24h_before(client, db, desk, marie, clinic):
    soon = datetime.now(UTC).replace(microsecond=0) + timedelta(hours=3)
    appointment = place(db, marie, clinic["anne"], clinic["evaluation"], soon)

    response = client.post(
        f"{DESK}/appointments/{appointment.id}/reschedule",
        json={"start": at(10).isoformat()},
        headers=headers(desk),
    )

    assert response.status_code == 200
    assert response.json()["start_local"].endswith("T10:00:00-05:00")
    assert last_history(db, appointment.id).reason.startswith("by phone: rescheduled from")


def test_desk_cannot_move_to_a_taken_time(client, db, desk, marie, clinic):
    appointment = place(db, marie, clinic["anne"], clinic["evaluation"], at(8))
    place(db, make_patient(db, "Luc"), clinic["anne"], clinic["evaluation"], at(10))

    response = client.post(
        f"{DESK}/appointments/{appointment.id}/reschedule",
        json={"start": at(10).isoformat(), "therapist_id": str(clinic["anne"].id)},
        headers=headers(desk),
    )

    assert response.status_code == 409


def test_unknown_appointment_gives_404(client, desk):
    for action in ("cancel", "check-in", "no-show"):
        response = client.post(
            f"{DESK}/appointments/{uuid.uuid4()}/{action}", headers=headers(desk)
        )
        assert response.status_code == 404, action


# --- Check-in and no-show (B-FRD-03) --------------------------------------------------


def today_at(hour):
    return local_to_utc(today_local(), time(hour))


def test_check_in_on_the_day(client, db, desk, marie, clinic):
    appointment = place(db, marie, clinic["anne"], clinic["evaluation"], today_at(12))

    response = client.post(f"{DESK}/appointments/{appointment.id}/check-in", headers=headers(desk))

    assert response.status_code == 200
    assert response.json()["status"] == "checked_in"
    assert last_history(db, appointment.id).changed_by == desk.id


def test_no_check_in_on_another_day(db, desk, marie, clinic):
    appointment = place(db, marie, clinic["anne"], clinic["evaluation"], at(8))
    user = db.get(User, desk.id)

    with pytest.raises(front_desk_service.BookingError, match="on the day"):
        front_desk_service.check_in(db, user, appointment.id, now=at(8) - timedelta(days=1))
    assert front_desk_service.check_in(db, user, appointment.id, now=at(7)).status == "checked_in"


def test_only_confirmed_appointments_are_checked_in(client, db, desk, marie, clinic):
    appointment = place(
        db, marie, clinic["anne"], clinic["evaluation"], today_at(12), status="cancelled_by_patient"
    )

    response = client.post(f"{DESK}/appointments/{appointment.id}/check-in", headers=headers(desk))

    assert response.status_code == 409


@pytest.mark.parametrize("minutes_after,allowed", [(0, False), (14, False), (15, True), (90, True)])
def test_no_show_only_15_minutes_after_the_start(db, desk, marie, clinic, minutes_after, allowed):
    start = at(8)
    appointment = place(db, marie, clinic["anne"], clinic["evaluation"], start)
    user = db.get(User, desk.id)
    now = start + timedelta(minutes=minutes_after)

    if allowed:
        assert (
            front_desk_service.mark_no_show(db, user, appointment.id, now=now).status == "no_show"
        )
    else:
        with pytest.raises(front_desk_service.BookingError, match="15 minutes"):
            front_desk_service.mark_no_show(db, user, appointment.id, now=now)


def test_no_show_through_the_api(client, db, desk, marie, clinic):
    started = datetime.now(UTC).replace(microsecond=0) - timedelta(minutes=30)
    appointment = place(db, marie, clinic["anne"], clinic["evaluation"], started)

    response = client.post(f"{DESK}/appointments/{appointment.id}/no-show", headers=headers(desk))

    assert response.status_code == 200
    assert response.json()["status"] == "no_show"
    assert "deposit kept" in last_history(db, appointment.id).reason


def test_checked_in_patient_is_not_marked_absent(client, db, desk, marie, clinic):
    started = datetime.now(UTC).replace(microsecond=0) - timedelta(minutes=30)
    appointment = place(
        db, marie, clinic["anne"], clinic["evaluation"], started, status="checked_in"
    )

    response = client.post(f"{DESK}/appointments/{appointment.id}/no-show", headers=headers(desk))

    assert response.status_code == 409


def test_desk_actions_need_mfa(client, db, desk, marie, clinic):
    from tests.test_availability import staff_token
    from tests.test_login import bearer

    appointment = place(db, marie, clinic["anne"], clinic["evaluation"], today_at(12))
    no_mfa = bearer(staff_token(desk.id, role="front_desk", mfa=False))

    response = client.post(f"{DESK}/appointments/{appointment.id}/check-in", headers=no_mfa)

    assert response.status_code == 403
