"""Demo data (D1): right amounts, valid appointments, safe to run twice."""

from sqlalchemy import func, select

from app.core.security import verify_password
from app.models import Appointment, AvailabilityRule, Patient, Service, Therapist, User
from app.seed import seed

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
