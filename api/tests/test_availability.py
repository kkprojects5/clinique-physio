"""Services, therapists, availability and slot search through the API (B-AVL-01 to 03)."""

import uuid
from datetime import UTC, datetime, time, timedelta

import pytest
from sqlalchemy.dialects.postgresql import Range

from app.core.security import create_token
from app.models import (
    Appointment,
    AvailabilityException,
    AvailabilityRule,
    Patient,
    Service,
    Therapist,
    TherapistService,
)
from app.services.availability_service import today_local
from app.services.slots import local_to_utc
from tests.test_login import bearer, make_user

SLOTS = "/api/v1/availability"
MY_AVAILABILITY = "/api/v1/therapist/availability"


def next_monday():
    today = today_local()
    return today + timedelta(days=7 - today.weekday() + 7)  # Monday at least a week ahead


def make_therapist(db, name="Lefebvre"):
    user = make_user(db, f"{name.lower()}-{uuid.uuid4().hex[:6]}@example.com", role="therapist")
    therapist = Therapist(
        user_id=user.id,
        first_name="Anne",
        last_name=name,
        licence_number=f"PHY-{uuid.uuid4().hex[:8]}",
        specialties=["sport"],
        languages=["fr", "en"],
    )
    db.add(therapist)
    db.commit()
    return therapist


def staff_token(user_id, role="therapist", mfa=True):
    return create_token(str(user_id), "access", timedelta(minutes=5), {"role": role, "mfa": mfa})


@pytest.fixture
def setup(db):
    service = Service(
        name_fr="Suivi 30 min",
        name_en="Follow-up 30 min",
        duration_min=30,
        price_cents=8000,
        deposit_cents=2000,
    )
    db.add(service)
    db.flush()
    therapist = make_therapist(db)
    db.add(TherapistService(therapist_id=therapist.id, service_id=service.id))
    db.add(
        AvailabilityRule(therapist_id=therapist.id, weekday=1, start_time=time(8), end_time=time(9))
    )
    db.commit()
    return service, therapist


def search(client, service, day, **params):
    query = {"service_id": str(service.id), "date_from": str(day), "date_to": str(day), **params}
    return client.get(SLOTS, params=query)


def local_starts(response):
    return [s["start_local"][11:16] for s in response.json()]


# --- Public catalog ----------------------------------------------------------


def test_services_list_active_services_with_their_therapists(client, db, setup):
    service, therapist = setup
    db.add(
        Service(
            name_fr="Ancien",
            name_en="Old",
            duration_min=30,
            price_cents=1,
            deposit_cents=0,
            is_active=False,
        )
    )
    db.commit()

    body = client.get("/api/v1/services").json()

    assert [s["name_en"] for s in body] == ["Follow-up 30 min"]
    assert body[0]["therapist_ids"] == [str(therapist.id)]


def test_therapists_list_shows_public_info_only(client, setup):
    body = client.get("/api/v1/therapists").json()

    assert body[0]["last_name"] == "Lefebvre"
    assert "licence_number" not in body[0]
    assert "user_id" not in body[0]


# --- Slot search -------------------------------------------------------------


def test_slots_for_a_working_morning(client, setup):
    service, _ = setup

    response = search(client, service, next_monday())

    assert response.status_code == 200
    assert local_starts(response) == ["08:00", "08:15", "08:30"]
    assert response.json()[0]["start_local"].endswith(("-04:00", "-05:00"))  # Montreal time


def test_booked_appointment_and_buffer_remove_slots(client, db, setup):
    service, therapist = setup
    day = next_monday()
    patient_user = make_user(db, "p@example.com")
    patient = Patient(
        user_id=patient_user.id,
        first_name="P",
        last_name="P",
        date_of_birth=datetime(1990, 1, 1).date(),
        phone="5145550000",
    )
    db.add(patient)
    db.flush()
    db.add(
        Appointment(
            patient_id=patient.id,
            therapist_id=therapist.id,
            service_id=service.id,
            during=Range(local_to_utc(day, time(8, 30)), local_to_utc(day, time(9, 0))),
            status="confirmed",
            created_by=patient_user.id,
        )
    )
    db.commit()

    assert local_starts(search(client, service, day)) == []  # 08:00-08:30 is within the buffer


def test_expired_hold_does_not_block_but_active_hold_does(client, db, setup):
    service, therapist = setup
    day = next_monday()
    patient_user = make_user(db, "p@example.com")
    patient = Patient(
        user_id=patient_user.id,
        first_name="P",
        last_name="P",
        date_of_birth=datetime(1990, 1, 1).date(),
        phone="5145550000",
    )
    db.add(patient)
    db.flush()
    hold = Appointment(
        patient_id=patient.id,
        therapist_id=therapist.id,
        service_id=service.id,
        during=Range(local_to_utc(day, time(8, 0)), local_to_utc(day, time(8, 30))),
        status="held",
        created_by=patient_user.id,
        hold_expires_at=datetime.now(UTC) - timedelta(minutes=1),
    )
    db.add(hold)
    db.commit()
    assert "08:00" in local_starts(search(client, service, day))

    hold.hold_expires_at = datetime.now(UTC) + timedelta(minutes=9)
    db.commit()
    assert "08:00" not in local_starts(search(client, service, day))


def test_time_off_removes_slots(client, db, setup):
    service, therapist = setup
    day = next_monday()
    db.add(
        AvailabilityException(
            therapist_id=therapist.id,
            reason="training",
            during=Range(local_to_utc(day, time(8)), local_to_utc(day, time(12))),
        )
    )
    db.commit()

    assert search(client, service, day).json() == []


def test_first_available_combines_therapists(client, db, setup):
    service, first = setup
    second = make_therapist(db, name="Nguyen")
    db.add(TherapistService(therapist_id=second.id, service_id=service.id))
    db.add(
        AvailabilityRule(
            therapist_id=second.id, weekday=1, start_time=time(8), end_time=time(8, 30)
        )
    )
    db.commit()

    body = search(client, service, next_monday()).json()
    only_second = search(client, service, next_monday(), therapist_id=str(second.id)).json()

    assert {s["therapist_id"] for s in body} == {str(first.id), str(second.id)}
    assert len(only_second) == 1


def test_therapist_not_providing_the_service_has_no_slots(client, db, setup):
    service, _ = setup
    other = make_therapist(db, name="Roy")

    assert search(client, service, next_monday(), therapist_id=str(other.id)).json() == []


@pytest.mark.parametrize(
    ("offset_from", "offset_to"),
    [(10, 5), (0, 40)],  # end before start; more than 31 days
)
def test_invalid_ranges_are_refused(client, setup, offset_from, offset_to):
    service, _ = setup
    today = today_local()
    params = {
        "service_id": str(service.id),
        "date_from": str(today + timedelta(days=offset_from)),
        "date_to": str(today + timedelta(days=offset_to)),
    }

    assert client.get(SLOTS, params=params).status_code == 422


def test_unknown_service_is_refused(client, setup):
    params = {
        "service_id": str(uuid.uuid4()),
        "date_from": str(next_monday()),
        "date_to": str(next_monday()),
    }

    assert client.get(SLOTS, params=params).status_code == 422


def test_no_slots_more_than_60_days_ahead(client, setup):
    service, _ = setup
    far = today_local() + timedelta(days=70)

    assert search(client, service, far).json() == []


def test_no_slots_in_the_past(client, setup):
    service, _ = setup
    last_week = today_local() - timedelta(days=7)

    assert search(client, service, last_week).json() == []


# --- Therapist manages own availability (B-AVL-02) ---------------------------


def test_therapist_replaces_weekly_schedule(client, setup):
    _, therapist = setup
    headers = bearer(staff_token(therapist.user_id))
    rules = {
        "rules": [
            {"weekday": 2, "start_time": "09:00", "end_time": "12:00"},
            {"weekday": 2, "start_time": "13:00", "end_time": "17:00"},
        ]
    }

    response = client.put(MY_AVAILABILITY, json=rules, headers=headers)

    assert response.status_code == 200
    assert [r["weekday"] for r in response.json()["rules"]] == [2, 2]
    assert (
        client.get(MY_AVAILABILITY, headers=headers).json()["rules"][0]["start_time"] == "09:00:00"
    )


@pytest.mark.parametrize(
    "rules",
    [
        [{"weekday": 1, "start_time": "10:00", "end_time": "09:00"}],
        [
            {"weekday": 1, "start_time": "08:00", "end_time": "12:00"},
            {"weekday": 1, "start_time": "11:00", "end_time": "14:00"},
        ],
        [{"weekday": 8, "start_time": "08:00", "end_time": "12:00"}],
    ],
)
def test_invalid_schedules_are_refused(client, setup, rules):
    _, therapist = setup

    response = client.put(
        MY_AVAILABILITY, json={"rules": rules}, headers=bearer(staff_token(therapist.user_id))
    )

    assert response.status_code == 422


def test_therapist_adds_and_deletes_own_time_off(client, setup):
    service, therapist = setup
    headers = bearer(staff_token(therapist.user_id))
    day = next_monday()
    body = {
        "starts_at": local_to_utc(day, time(0)).isoformat(),
        "ends_at": local_to_utc(day, time(23, 59)).isoformat(),
        "reason": "vacation",
    }

    created = client.post(f"{MY_AVAILABILITY}/exceptions", json=body, headers=headers)
    assert created.status_code == 201
    assert search(client, service, day).json() == []

    deleted = client.delete(f"{MY_AVAILABILITY}/exceptions/{created.json()['id']}", headers=headers)
    assert deleted.status_code == 204
    assert search(client, service, day).json() != []


def test_therapist_cannot_delete_another_therapists_time_off(client, db, setup):
    _, owner = setup
    intruder = make_therapist(db, name="Intrus")
    exception = AvailabilityException(
        therapist_id=owner.id,
        during=Range(datetime.now(UTC), datetime.now(UTC) + timedelta(hours=1)),
    )
    db.add(exception)
    db.commit()

    response = client.delete(
        f"{MY_AVAILABILITY}/exceptions/{exception.id}",
        headers=bearer(staff_token(intruder.user_id)),
    )

    assert response.status_code == 404
    assert db.get(AvailabilityException, exception.id) is not None


def test_time_off_needs_time_zone(client, setup):
    _, therapist = setup
    body = {"starts_at": "2030-01-07T08:00:00", "ends_at": "2030-01-07T12:00:00"}

    response = client.post(
        f"{MY_AVAILABILITY}/exceptions", json=body, headers=bearer(staff_token(therapist.user_id))
    )

    assert response.status_code == 422


def test_only_therapists_with_mfa_manage_availability(client, db, setup):
    _, therapist = setup
    patient = make_user(db, "patient@example.com")
    desk = make_user(db, "desk@example.com", role="front_desk")

    no_mfa = client.get(MY_AVAILABILITY, headers=bearer(staff_token(therapist.user_id, mfa=False)))
    as_patient = client.get(
        MY_AVAILABILITY, headers=bearer(staff_token(patient.id, role="patient"))
    )
    as_desk = client.get(MY_AVAILABILITY, headers=bearer(staff_token(desk.id, role="front_desk")))

    assert no_mfa.status_code == as_patient.status_code == as_desk.status_code == 403
