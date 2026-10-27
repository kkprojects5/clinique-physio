"""Challenge B-C1: double booking under concurrency.

30 patients try to book the same therapist at the same time, all at once.
The database exclusion constraint must accept exactly one and refuse the 29 others.

Needs a running database with the migrations applied (alembic upgrade head).
"""

import threading
import uuid
from collections import Counter
from datetime import UTC, date, datetime, timedelta

import pytest
from psycopg.errors import ExclusionViolation
from sqlalchemy import create_engine, delete
from sqlalchemy.dialects.postgresql import Range
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.session import SessionLocal
from app.models import Appointment, Patient, Service, Therapist, User

REQUESTS = 30


def make_user(session, role: str) -> User:
    user = User(email=f"{uuid.uuid4()}@test.invalid", password_hash="not-a-real-hash", role=role)
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def setup_data():
    """Create 1 therapist, 1 service and 30 patients; delete everything afterwards."""
    with SessionLocal() as session:
        therapist_user = make_user(session, "therapist")
        therapist = Therapist(
            user_id=therapist_user.id,
            first_name="Test",
            last_name="Therapist",
            licence_number=f"TEST-{uuid.uuid4()}",
        )
        service = Service(
            name_fr="Suivi 30 min",
            name_en="Follow-up 30 min",
            duration_min=30,
            price_cents=8000,
            deposit_cents=2000,
        )
        session.add_all([therapist, service])
        session.flush()

        patients = []
        for i in range(REQUESTS):
            user = make_user(session, "patient")
            patient = Patient(
                user_id=user.id,
                first_name="Test",
                last_name=f"Patient{i}",
                date_of_birth=date(1990, 1, 1),
                phone="514-555-0000",
            )
            session.add(patient)
            patients.append(patient)
        session.commit()
        data = {
            "therapist_id": therapist.id,
            "service_id": service.id,
            "patients": [(p.id, p.user_id) for p in patients],
            "user_ids": [therapist_user.id] + [p.user_id for p in patients],
        }

    yield data

    with SessionLocal() as session:
        session.execute(delete(Appointment).where(Appointment.therapist_id == data["therapist_id"]))
        session.execute(delete(Patient).where(Patient.user_id.in_(data["user_ids"])))
        session.execute(delete(Therapist).where(Therapist.id == data["therapist_id"]))
        session.execute(delete(Service).where(Service.id == data["service_id"]))
        session.execute(delete(User).where(User.id.in_(data["user_ids"])))
        session.commit()


def test_30_concurrent_bookings_only_one_succeeds(setup_data):
    start = datetime(2030, 3, 4, 15, 0, tzinfo=UTC)
    slot = Range(start, start + timedelta(minutes=30))  # same slot for everybody
    barrier = threading.Barrier(REQUESTS)  # makes all threads insert at the same moment
    results: list[str] = []
    lock = threading.Lock()

    # One connection per thread, so no thread waits for a free connection.
    engine = create_engine(settings.database_url, pool_size=REQUESTS, max_overflow=0)
    make_session = sessionmaker(bind=engine, expire_on_commit=False)

    def book(patient_id, user_id):
        try:
            with make_session() as session:
                session.add(
                    Appointment(
                        patient_id=patient_id,
                        therapist_id=setup_data["therapist_id"],
                        service_id=setup_data["service_id"],
                        during=slot,
                        status="pending_payment",
                        created_by=user_id,
                    )
                )
                barrier.wait(timeout=30)
                try:
                    session.commit()
                    outcome = "booked"
                except IntegrityError as error:
                    session.rollback()
                    # Only the no-overlap constraint is an acceptable reason to fail.
                    if isinstance(error.orig, ExclusionViolation):
                        outcome = "slot_taken"
                    else:
                        outcome = f"other integrity error: {error.orig!r}"
        except Exception as error:  # noqa: BLE001  (record it so the failure message shows it)
            outcome = f"unexpected {type(error).__name__}: {error}"[:300]
        with lock:
            results.append(outcome)

    threads = [threading.Thread(target=book, args=p) for p in setup_data["patients"]]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    engine.dispose()

    summary = Counter(results)
    assert summary["booked"] == 1, summary
    assert summary["slot_taken"] == REQUESTS - 1, summary


def test_cancelled_appointment_frees_the_slot(setup_data):
    start = datetime(2030, 3, 5, 15, 0, tzinfo=UTC)
    slot = Range(start, start + timedelta(minutes=30))
    (p1, u1), (p2, u2) = setup_data["patients"][:2]

    with SessionLocal() as session:
        first = Appointment(
            patient_id=p1,
            therapist_id=setup_data["therapist_id"],
            service_id=setup_data["service_id"],
            during=slot,
            status="confirmed",
            created_by=u1,
        )
        session.add(first)
        session.commit()

        first.status = "cancelled_by_patient"
        session.commit()

        # The constraint ignores cancelled appointments, so the slot can be booked again.
        session.add(
            Appointment(
                patient_id=p2,
                therapist_id=setup_data["therapist_id"],
                service_id=setup_data["service_id"],
                during=slot,
                status="confirmed",
                created_by=u2,
            )
        )
        session.commit()
