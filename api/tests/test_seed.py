"""Demo data (D1): right amounts, valid appointments, safe to run twice."""

from sqlalchemy import func, select

from app.core.security import verify_password
from app.models import Appointment, AvailabilityRule, Patient, Service, Therapist, User
from app.seed import refresh_appointments, seed

STAFF = "Staff-Demo-Password-1"
PATIENTS = "Patient-Demo-Password-1"


def count(db, model):
    return db.scalar(select(func.count()).select_from(model))


def test_seed_creates_the_d1_demo_data(db):
    assert seed(db, STAFF, PATIENTS) is True

    assert count(db, Therapist) == 6
    assert count(db, Patient) == 50
    assert count(db, Service) == 5
    assert db.scalar(select(func.count()).where(User.role == "front_desk")) == 2
    assert db.scalar(select(func.count()).where(User.role == "admin")) == 1
    assert count(db, AvailabilityRule) > 0
    assert count(db, Appointment) > 0  # something for the desktop and mobile apps to show


def test_seed_accounts_are_verified_and_use_the_given_passwords(db):
    seed(db, STAFF, PATIENTS)

    admin = db.scalar(select(User).where(User.role == "admin"))
    patient = db.scalar(select(User).where(User.role == "patient").limit(1))
    assert admin.email_verified_at is not None
    assert verify_password(admin.password_hash, STAFF)
    assert verify_password(patient.password_hash, PATIENTS)
    assert not verify_password(patient.password_hash, STAFF)


def test_seed_uses_only_reserved_example_addresses_and_numbers(db):
    seed(db, STAFF, PATIENTS)

    emails = db.scalars(select(User.email)).all()
    phones = db.scalars(select(Patient.phone)).all()
    assert all(e.endswith("example.com") for e in emails)
    assert all("-555-" in p for p in phones)


def test_seed_is_safe_to_run_twice(db):
    seed(db, STAFF, PATIENTS)

    assert seed(db, STAFF, PATIENTS) is False
    assert count(db, Therapist) == 6


def test_refresh_adds_appointments_on_empty_days_only(db):
    seed(db, STAFF, PATIENTS)
    db.query(Appointment).delete()  # simulate the demo appointments being in the past
    db.commit()

    first = refresh_appointments(db, rng_seed=1)
    second = refresh_appointments(db, rng_seed=2)

    assert first > 0
    assert second == 0  # every day already has appointments: nothing added, nothing doubled
    assert count(db, Appointment) == first


def test_refresh_never_creates_overlaps(db):
    seed(db, STAFF, PATIENTS)
    refresh_appointments(db, rng_seed=3)

    # The database exclusion constraint would have refused any overlap; check the rule anyway.
    rows = db.scalars(select(Appointment).order_by(Appointment.therapist_id, Appointment.during))
    previous = None
    for appointment in rows:
        if previous is not None and previous.therapist_id == appointment.therapist_id:
            assert previous.during.upper <= appointment.during.lower
        previous = appointment


def test_refresh_does_nothing_without_demo_data(db):
    assert refresh_appointments(db) == 0
