"""Online booking: hold, cancel, reschedule, status history (B-BKG-01 to 06)."""

from datetime import UTC, date, datetime, time, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import Range

from app.models import (
    Appointment,
    AppointmentStatusHistory,
    AvailabilityRule,
    Service,
    TherapistService,
    User,
)
from app.services import booking_service
from app.services.slots import local_to_utc
from tests.test_availability import SLOTS, make_therapist, next_monday, staff_token
from tests.test_login import bearer
from tests.test_schedules import make_patient, patient_headers

HOLD = "/api/v1/appointments/hold"


def cancel_url(appointment_id):
    return f"/api/v1/appointments/{appointment_id}/cancel"


def reschedule_url(appointment_id):
    return f"/api/v1/appointments/{appointment_id}/reschedule"


@pytest.fixture
def clinic(db):
    """Two therapists working Monday 8:00 to 12:00; an evaluation and a treatment."""
    evaluation = Service(
        name_fr="Évaluation",
        name_en="Evaluation",
        duration_min=60,
        price_cents=12000,
        deposit_cents=3000,
        is_initial_evaluation=True,
    )
    treatment = Service(
        name_fr="Traitement",
        name_en="Treatment",
        duration_min=30,
        price_cents=8000,
        deposit_cents=2000,
    )
    db.add_all([evaluation, treatment])
    db.flush()
    anne, sophie = make_therapist(db, "Lefebvre"), make_therapist(db, "Nguyen")
    for therapist in (anne, sophie):
        for service in (evaluation, treatment):
            db.add(TherapistService(therapist_id=therapist.id, service_id=service.id))
        db.add(
            AvailabilityRule(
                therapist_id=therapist.id, weekday=1, start_time=time(8), end_time=time(12)
            )
        )
    db.commit()
    return {"evaluation": evaluation, "treatment": treatment, "anne": anne, "sophie": sophie}


def at(hour, minute=0, day=None):
    """A Monday time in Montréal, as the API expects it (with its time zone)."""
    return local_to_utc(day or next_monday(), time(hour, minute))


def hold(client, patient, service, start, therapist=None):
    body = {"service_id": str(service.id), "start": start.isoformat()}
    if therapist is not None:
        body["therapist_id"] = str(therapist.id)
    return client.post(HOLD, json=body, headers=patient_headers(patient))


def place(db, patient, therapist, service, start, status="confirmed", hold_expires_at=None):
    appointment = Appointment(
        patient_id=patient.id,
        therapist_id=therapist.id,
        service_id=service.id,
        during=Range(start, start + timedelta(minutes=service.duration_min)),
        status=status,
        created_by=patient.user_id,
        hold_expires_at=hold_expires_at,
    )
    db.add(appointment)
    db.commit()
    return appointment


def history(db, appointment_id):
    return db.scalars(
        select(AppointmentStatusHistory)
        .where(AppointmentStatusHistory.appointment_id == appointment_id)
        .order_by(AppointmentStatusHistory.changed_at, AppointmentStatusHistory.to_status)
    ).all()


def offered(client, service, day=None):
    day = day or next_monday()
    params = {"service_id": str(service.id), "date_from": str(day), "date_to": str(day)}
    return {s["start"] for s in client.get(SLOTS, params=params).json()}


# --- Hold ------------------------------------------------------------------------


def test_hold_keeps_the_slot_10_minutes(client, db, clinic):
    marie = make_patient(db, "Marie")
    start = at(8)

    response = hold(client, marie, clinic["evaluation"], start, clinic["anne"])

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "held"
    assert body["start_local"].endswith("T08:00:00-05:00")
    assert body["deposit_cents"] == 3000
    expires = datetime.fromisoformat(body["hold_expires_at"])
    assert timedelta(minutes=9) < expires - datetime.now(UTC) <= timedelta(minutes=10)
    rows = history(db, body["id"])
    assert [(r.from_status, r.to_status, r.changed_by) for r in rows] == [
        (None, "held", marie.user_id)
    ]


def test_held_slot_disappears_from_the_public_search(client, db, clinic):
    start = at(8)
    hold(client, make_patient(db, "Marie"), clinic["evaluation"], start, clinic["anne"])

    params = {
        "service_id": str(clinic["evaluation"].id),
        "therapist_id": str(clinic["anne"].id),
        "date_from": str(next_monday()),
        "date_to": str(next_monday()),
    }
    starts = {s["start"] for s in client.get(SLOTS, params=params).json()}
    assert not any(s.startswith(start.isoformat()[:16]) for s in starts)


@pytest.mark.parametrize("hour,minute", [(9, 7), (13, 0), (7, 0)])
def test_only_times_the_clinic_offers_can_be_held(client, db, clinic, hour, minute):
    response = hold(client, make_patient(db, "Marie"), clinic["evaluation"], at(hour, minute))

    assert response.status_code == 409


def test_time_without_time_zone_is_refused(client, db, clinic):
    body = {"service_id": str(clinic["evaluation"].id), "start": f"{next_monday()}T08:00:00"}
    response = client.post(HOLD, json=body, headers=patient_headers(make_patient(db, "Marie")))

    assert response.status_code == 422


def test_a_slot_already_held_gives_409(client, db, clinic):
    start = at(8)
    assert (
        hold(
            client, make_patient(db, "Marie"), clinic["evaluation"], start, clinic["anne"]
        ).status_code
        == 201
    )

    response = hold(client, make_patient(db, "Luc"), clinic["evaluation"], start, clinic["anne"])

    assert response.status_code == 409
    assert "no longer available" in response.json()["detail"]


def test_first_available_picks_a_free_therapist(client, db, clinic):
    start = at(8)
    hold(client, make_patient(db, "Marie"), clinic["evaluation"], start, clinic["anne"])

    response = hold(client, make_patient(db, "Luc"), clinic["evaluation"], start)

    assert response.status_code == 201
    assert response.json()["therapist"]["last_name"] == "Nguyen"


def test_an_expired_hold_frees_the_slot(client, db, clinic):
    start = at(8)
    old = place(
        db,
        make_patient(db, "Marie"),
        clinic["anne"],
        clinic["evaluation"],
        start,
        status="held",
        hold_expires_at=datetime.now(UTC) - timedelta(minutes=1),
    )

    response = hold(client, make_patient(db, "Luc"), clinic["evaluation"], start, clinic["anne"])

    assert response.status_code == 201
    db.refresh(old)
    assert old.status == "expired"
    assert history(db, old.id)[-1].changed_by is None  # done by the system


def test_a_new_hold_replaces_the_patients_previous_hold(client, db, clinic):
    marie = make_patient(db, "Marie")
    first = hold(client, marie, clinic["evaluation"], at(8), clinic["anne"]).json()

    second = hold(client, marie, clinic["evaluation"], at(10), clinic["anne"])

    assert second.status_code == 201
    assert db.get(Appointment, first["id"]).status == "expired"
    # the first slot is free again for someone else
    assert (
        hold(
            client, make_patient(db, "Luc"), clinic["evaluation"], at(8), clinic["anne"]
        ).status_code
        == 201
    )


def test_a_treatment_needs_an_initial_evaluation_first(client, db, clinic):
    marie = make_patient(db, "Marie")

    refused = hold(client, marie, clinic["treatment"], at(10), clinic["anne"])
    assert refused.status_code == 409
    assert "initial evaluation" in refused.json()["detail"]

    place(db, marie, clinic["sophie"], clinic["evaluation"], at(8))
    assert hold(client, marie, clinic["treatment"], at(10), clinic["anne"]).status_code == 201


def test_a_refused_hold_keeps_the_previous_hold(client, db, clinic):
    marie = make_patient(db, "Marie")
    first = hold(client, marie, clinic["evaluation"], at(8), clinic["anne"]).json()

    assert hold(client, marie, clinic["evaluation"], at(13), clinic["anne"]).status_code == 409

    assert db.get(Appointment, first["id"]).status == "held"


def test_only_patients_can_book(client, db, clinic):
    body = {"service_id": str(clinic["evaluation"].id), "start": at(8).isoformat()}
    therapist_user = db.get(User, clinic["anne"].user_id)

    assert client.post(HOLD, json=body).status_code == 401
    staff = bearer(staff_token(therapist_user.id, role="therapist"))
    assert client.post(HOLD, json=body, headers=staff).status_code == 403


# --- Cancel ----------------------------------------------------------------------


def test_cancel_a_paid_appointment_more_than_24h_before_refunds(client, db, clinic):
    marie = make_patient(db, "Marie")
    appointment = place(db, marie, clinic["anne"], clinic["evaluation"], at(8))

    response = client.post(cancel_url(appointment.id), headers=patient_headers(marie))

    assert response.status_code == 200
    assert response.json()["deposit_refunded"] is True
    assert response.json()["appointment"]["status"] == "cancelled_by_patient"
    last = history(db, appointment.id)[-1]
    assert (last.from_status, last.to_status, last.reason) == (
        "confirmed",
        "cancelled_by_patient",
        "deposit refunded",
    )
    assert at(8).isoformat()[:16] in {s[:16] for s in offered(client, clinic["evaluation"])}


def test_cancel_less_than_24h_before_keeps_the_deposit(client, db, clinic):
    marie = make_patient(db, "Marie")
    soon = datetime.now(UTC).replace(microsecond=0) + timedelta(hours=3)
    appointment = place(db, marie, clinic["anne"], clinic["evaluation"], soon)

    response = client.post(cancel_url(appointment.id), headers=patient_headers(marie))

    assert response.json()["deposit_refunded"] is False
    assert "deposit kept" in history(db, appointment.id)[-1].reason


def test_cancel_an_unpaid_hold(client, db, clinic):
    marie = make_patient(db, "Marie")
    held = hold(client, marie, clinic["evaluation"], at(8), clinic["anne"]).json()

    response = client.post(cancel_url(held["id"]), headers=patient_headers(marie))

    assert response.json()["deposit_refunded"] is False
    assert response.json()["appointment"]["status"] == "cancelled_by_patient"


def test_patients_cannot_cancel_someone_elses_appointment(client, db, clinic):
    appointment = place(db, make_patient(db, "Marie"), clinic["anne"], clinic["evaluation"], at(8))

    response = client.post(
        cancel_url(appointment.id), headers=patient_headers(make_patient(db, "Luc"))
    )

    assert response.status_code == 404  # same answer as a missing appointment
    db.refresh(appointment)
    assert appointment.status == "confirmed"


def test_cannot_cancel_twice_or_after_the_start(client, db, clinic):
    marie = make_patient(db, "Marie")
    appointment = place(db, marie, clinic["anne"], clinic["evaluation"], at(8))
    client.post(cancel_url(appointment.id), headers=patient_headers(marie))
    past = place(
        db,
        marie,
        clinic["anne"],
        clinic["evaluation"],
        datetime.now(UTC).replace(microsecond=0) - timedelta(hours=2),
    )

    assert (
        client.post(cancel_url(appointment.id), headers=patient_headers(marie)).status_code == 409
    )
    assert client.post(cancel_url(past.id), headers=patient_headers(marie)).status_code == 409


# --- The 24-hour rule across the daylight saving change ----------------------------


def toronto(day, hour, minute=0):
    return local_to_utc(day, time(hour, minute))


@pytest.mark.parametrize(
    "now_local,refunded",
    [
        ((date(2026, 10, 31), 10, 0), True),  # 25 real hours before
        ((date(2026, 10, 31), 10, 59), True),  # 24 h 1 min before, although clocks say 23 h
        ((date(2026, 10, 31), 11, 0), False),  # exactly 24 real hours: not more than 24 h
        ((date(2026, 11, 1), 9, 0), False),  # 1 hour before
    ],
)
def test_24_hours_are_real_hours_across_the_november_change(db, clinic, now_local, refunded):
    # Clocks go back on Sunday 1 November 2026 at 2:00, so that Sunday has 25 hours.
    marie = make_patient(db, "Marie")
    start = toronto(date(2026, 11, 1), 10)
    appointment = place(db, marie, clinic["anne"], clinic["evaluation"], start)
    user = db.get(User, marie.user_id)

    _, result = booking_service.cancel(db, marie, user, appointment.id, now=toronto(*now_local))

    assert result is refunded


# --- Reschedule --------------------------------------------------------------------


def test_reschedule_to_another_free_time(client, db, clinic):
    marie = make_patient(db, "Marie")
    appointment = place(db, marie, clinic["anne"], clinic["evaluation"], at(8))

    response = client.post(
        reschedule_url(appointment.id),
        json={"start": at(10).isoformat()},
        headers=patient_headers(marie),
    )

    assert response.status_code == 200
    assert response.json()["start_local"].endswith("T10:00:00-05:00")
    assert response.json()["status"] == "confirmed"
    assert history(db, appointment.id)[-1].reason.startswith("rescheduled from")
    # the old time is free again
    assert (
        hold(
            client, make_patient(db, "Luc"), clinic["evaluation"], at(8), clinic["anne"]
        ).status_code
        == 201
    )


def test_reschedule_to_a_taken_time_gives_409_and_changes_nothing(client, db, clinic):
    marie = make_patient(db, "Marie")
    appointment = place(db, marie, clinic["anne"], clinic["evaluation"], at(8))
    place(db, make_patient(db, "Luc"), clinic["anne"], clinic["evaluation"], at(10))

    response = client.post(
        reschedule_url(appointment.id),
        json={"start": at(10).isoformat()},
        headers=patient_headers(marie),
    )

    assert response.status_code == 409
    db.refresh(appointment)
    assert appointment.during.lower == at(8)


def test_reschedule_less_than_24h_before_is_refused(client, db, clinic):
    marie = make_patient(db, "Marie")
    soon = datetime.now(UTC).replace(microsecond=0) + timedelta(hours=3)
    appointment = place(db, marie, clinic["anne"], clinic["evaluation"], soon)

    response = client.post(
        reschedule_url(appointment.id),
        json={"start": at(10).isoformat()},
        headers=patient_headers(marie),
    )

    assert response.status_code == 409
    assert "call the clinic" in response.json()["detail"]


def test_only_confirmed_appointments_can_be_rescheduled(client, db, clinic):
    marie = make_patient(db, "Marie")
    held = hold(client, marie, clinic["evaluation"], at(8), clinic["anne"]).json()

    response = client.post(
        reschedule_url(held["id"]),
        json={"start": at(10).isoformat()},
        headers=patient_headers(marie),
    )

    assert response.status_code == 409


def test_patients_cannot_reschedule_someone_elses_appointment(client, db, clinic):
    appointment = place(db, make_patient(db, "Marie"), clinic["anne"], clinic["evaluation"], at(8))

    response = client.post(
        reschedule_url(appointment.id),
        json={"start": at(10).isoformat()},
        headers=patient_headers(make_patient(db, "Luc")),
    )

    assert response.status_code == 404


# --- Schedules ignore expired holds -------------------------------------------------


def test_my_appointments_hide_expired_holds(client, db, clinic):
    marie = make_patient(db, "Marie")
    place(db, marie, clinic["anne"], clinic["evaluation"], at(8), status="expired")
    place(db, marie, clinic["anne"], clinic["evaluation"], at(10))

    body = client.get("/api/v1/me/appointments", headers=patient_headers(marie)).json()

    assert [a["status"] for a in body] == ["confirmed"]


def test_race_lost_at_the_database_gives_409(client, db, clinic, monkeypatch):
    """Two patients pass the free-slot check at the same moment; the database keeps one."""
    start = at(8)
    place(db, make_patient(db, "Marie"), clinic["anne"], clinic["evaluation"], start)
    # Pretend the check ran just before Marie's booking was saved.
    monkeypatch.setattr(booking_service, "_offered_slot", lambda *args: clinic["anne"].id)

    response = hold(client, make_patient(db, "Luc"), clinic["evaluation"], start, clinic["anne"])

    assert response.status_code == 409
    assert "no longer available" in response.json()["detail"]
