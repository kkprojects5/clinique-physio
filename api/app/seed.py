"""Demo data for development and the demo deployment (D1).

Creates 6 therapists with weekly schedules, 2 front-desk agents, 1 admin,
5 services, 50 fictional patients and some confirmed appointments.

All people are fictional. Emails use example.com and phone numbers use 555,
both reserved for examples, so no real person can be reached.

Run from the api folder:
    python -m app.seed                          # create the demo data (once)
    python -m app.seed --refresh-appointments   # add appointments for the next 2 weeks

Passwords are read from SEED_STAFF_PASSWORD and SEED_PATIENT_PASSWORD (.env).
They are never written in the code or the README (spec 7.3).
"""

import os
import random
import sys
import uuid
from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import Range
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.crypto import encrypt
from app.core.security import hash_password
from app.models import (
    ACTIVE_STATUSES,
    Appointment,
    AvailabilityRule,
    Consent,
    Patient,
    Service,
    Therapist,
    TherapistService,
    User,
)
from app.services import availability_service
from app.services.slots import BUFFER_MINUTES, CLINIC_TZ, local_to_utc

MIN_PASSWORD_LENGTH = 12

SERVICES = [
    # name_fr, name_en, minutes, price $, deposit $, initial evaluation?, key
    ("Évaluation initiale", "Initial evaluation", 60, 120, 30, True, "eval"),
    ("Traitement de suivi 30 min", "Follow-up treatment 30 min", 30, 80, 20, False, "f30"),
    ("Traitement de suivi 45 min", "Follow-up treatment 45 min", 45, 95, 25, False, "f45"),
    ("Réadaptation sportive", "Sports rehabilitation", 45, 100, 25, False, "sport"),
    (
        "Réadaptation post-chirurgicale",
        "Post-surgery rehabilitation",
        60,
        120,
        30,
        False,
        "surgery",
    ),
]

# first, last, specialties, languages, extra service keys, weekly schedule
THERAPISTS = [
    (
        "Anne",
        "Lefebvre",
        ["sport", "knee"],
        ["fr", "en"],
        ["sport"],
        {1: (8, 16), 2: (8, 16), 3: (8, 16), 4: (8, 16)},
    ),
    (
        "Karim",
        "Haddad",
        ["post-surgery", "shoulder"],
        ["fr", "en", "ar"],
        ["surgery"],
        {1: (10, 18), 3: (10, 18), 5: (8, 14)},
    ),
    (
        "Sophie",
        "Nguyen",
        ["back", "posture"],
        ["fr", "en", "vi"],
        [],
        {2: (9, 17), 4: (9, 17), 5: (9, 15)},
    ),
    (
        "Marc",
        "Tremblay",
        ["sport", "ankle"],
        ["fr"],
        ["sport"],
        {1: (7, 15), 2: (7, 15), 3: (7, 15)},
    ),
    (
        "Elena",
        "Petrova",
        ["post-surgery", "hip"],
        ["fr", "en", "ru"],
        ["surgery"],
        {2: (12, 20), 3: (12, 20), 4: (12, 20)},
    ),
    (
        "David",
        "Cohen",
        ["sport", "neck"],
        ["en", "fr"],
        ["sport", "surgery"],
        {1: (8, 12), 4: (13, 19), 5: (8, 16)},
    ),
]

FIRST_NAMES = [
    "Marie",
    "Jean",
    "Chloé",
    "Luc",
    "Fatima",
    "Olivier",
    "Mei",
    "Samuel",
    "Léa",
    "Ahmed",
    "Julie",
    "Thomas",
    "Inès",
    "Gabriel",
    "Noor",
    "Émile",
    "Sara",
    "Hugo",
    "Yasmine",
    "Antoine",
    "Camille",
    "Rafael",
    "Zoé",
    "Nathan",
    "Amira",
]
LAST_NAMES = [
    "Gagnon",
    "Roy",
    "Côté",
    "Bouchard",
    "Gauthier",
    "Morin",
    "Lavoie",
    "Fortin",
    "Gagné",
    "Ouellet",
    "Pelletier",
    "Bélanger",
    "Lévesque",
    "Bergeron",
    "Leblanc",
    "Paquette",
    "Girard",
    "Simard",
    "Boucher",
    "Caron",
    "Beaulieu",
    "Cloutier",
]


def _require_password(name: str) -> str:
    value = os.environ.get(name) or getattr(settings, name.lower(), None)
    if not value or len(value) < MIN_PASSWORD_LENGTH:
        sys.exit(f"{name} must be set in .env (at least {MIN_PASSWORD_LENGTH} characters).")
    return value


def _user(email: str, password_hash: str, role: str, language: str = "fr") -> User:
    return User(
        email=email,
        password_hash=password_hash,
        role=role,
        language=language,
        email_verified_at=datetime.now(UTC),
    )


def seed(db: Session, staff_password: str, patient_password: str, rng_seed: int = 42) -> bool:
    """Create the demo data. Returns False (and changes nothing) if it already exists."""
    if db.scalar(select(Therapist.id).limit(1)) is not None:
        return False

    # Not for security: only picks fictional demo names and dates, the same every run.
    rng = random.Random(rng_seed)  # noqa: S311  # nosec B311
    staff_hash = hash_password(staff_password)
    patient_hash = hash_password(patient_password)

    services = {}
    for name_fr, name_en, minutes, price, deposit, initial, key in SERVICES:
        service = Service(
            name_fr=name_fr,
            name_en=name_en,
            description_fr=f"{name_fr} avec un ou une physiothérapeute.",
            description_en=f"{name_en} with a physiotherapist.",
            duration_min=minutes,
            price_cents=price * 100,
            deposit_cents=deposit * 100,
            is_initial_evaluation=initial,
        )
        db.add(service)
        services[key] = service
    db.flush()

    for number, (first, last, specialties, languages, extra, schedule) in enumerate(THERAPISTS, 1):
        user = _user(
            f"{first.lower()}.{last.lower()}@clinique.example.com", staff_hash, "therapist"
        )
        db.add(user)
        db.flush()
        therapist = Therapist(
            user_id=user.id,
            first_name=first,
            last_name=last,
            licence_number=f"PHY-DEMO-{number:04d}",  # fictional licence numbers
            specialties=specialties,
            languages=languages,
            bio_fr=f"Physiothérapeute, intérêt pour : {', '.join(specialties)}.",
            bio_en=f"Physiotherapist, special interest in: {', '.join(specialties)}.",
        )
        db.add(therapist)
        db.flush()
        for key in ["eval", "f30", "f45", *extra]:
            db.add(TherapistService(therapist_id=therapist.id, service_id=services[key].id))
        for weekday, (start, end) in schedule.items():
            db.add(
                AvailabilityRule(
                    therapist_id=therapist.id,
                    weekday=weekday,
                    start_time=time(start),
                    end_time=time(end),
                )
            )

    for i in (1, 2):
        db.add(_user(f"accueil{i}@clinique.example.com", staff_hash, "front_desk"))
    db.add(_user("admin@clinique.example.com", staff_hash, "admin"))

    patients = []
    for i in range(1, 51):
        language = "en" if i % 4 == 0 else "fr"
        user = _user(f"patient{i:02d}@example.com", patient_hash, "patient", language)
        db.add(user)
        db.flush()
        patient = Patient(
            user_id=user.id,
            first_name=rng.choice(FIRST_NAMES),
            last_name=rng.choice(LAST_NAMES),
            date_of_birth=date(rng.randint(1950, 2005), rng.randint(1, 12), rng.randint(1, 28)),
            phone=f"514-555-{i:04d}",
            emergency_contact_enc=encrypt(f"Contact {i} 514-555-9{i:03d}") if i % 3 == 0 else None,
        )
        db.add(patient)
        db.add(
            Consent(user_id=user.id, type="privacy_policy", version=settings.privacy_policy_version)
        )
        if i % 2 == 0:
            db.add(
                Consent(
                    user_id=user.id,
                    type="electronic_comms",
                    version=settings.privacy_policy_version,
                )
            )
        patients.append((patient, user))
    db.flush()

    _seed_appointments(db, services["f30"], [(p.id, u.id) for p, u in patients], rng)
    db.commit()
    return True


APPOINTMENT_DAYS = 14  # demo appointments cover the next two weeks


def _seed_appointments(
    db: Session,
    service: Service,
    patients: list[tuple[uuid.UUID, uuid.UUID]],
    rng: random.Random,
    busy_days: set[tuple[uuid.UUID, date]] | None = None,
) -> int:
    """Book about a third of the free 30-min slots of the next 2 weeks, never overlapping.

    patients: (patient_id, user_id) pairs. busy_days: (therapist, day) pairs to leave alone.
    Returns the number of appointments created.
    """
    busy_days = busy_days or set()
    start = availability_service.today_local() + timedelta(days=1)
    last_day = start + timedelta(days=APPOINTMENT_DAYS - 1)
    slots = availability_service.find_slots(db, service.id, None, start, last_day)
    last_end: dict = {}
    buffer = timedelta(minutes=BUFFER_MINUTES)
    created = 0
    for slot in slots:
        day = slot.period.start.astimezone(CLINIC_TZ).date()
        if (slot.therapist_id, day) in busy_days:
            continue
        previous_end = last_end.get(slot.therapist_id)
        if previous_end is not None and slot.period.start < previous_end + buffer:
            continue
        if rng.random() > 0.35:
            continue
        patient_id, user_id = rng.choice(patients)
        db.add(
            Appointment(
                patient_id=patient_id,
                therapist_id=slot.therapist_id,
                service_id=service.id,
                during=Range(slot.period.start, slot.period.end),
                status="confirmed",
                created_by=user_id,
            )
        )
        last_end[slot.therapist_id] = slot.period.end
        created += 1
    db.flush()
    return created


def refresh_appointments(db: Session, rng_seed: int | None = None) -> int:
    """Add demo appointments for the next two weeks, on days that have none yet.

    Days that already have appointments are left untouched, and only free slots are
    used, so running it again never creates overlaps or duplicates.
    """
    service = db.scalar(select(Service).where(Service.duration_min == 30).limit(1))
    patients = [(p.id, p.user_id) for p in db.scalars(select(Patient))]
    if service is None or not patients:
        return 0

    start = availability_service.today_local() + timedelta(days=1)
    window = Range(
        local_to_utc(start, time(0)),
        local_to_utc(start + timedelta(days=APPOINTMENT_DAYS), time(0)),
    )
    existing = db.scalars(
        select(Appointment).where(
            Appointment.during.overlaps(window), Appointment.status.in_(ACTIVE_STATUSES)
        )
    )
    busy = {(a.therapist_id, a.during.lower.astimezone(CLINIC_TZ).date()) for a in existing}

    # Not for security: only picks fictional demo patients and times.
    rng = random.Random(rng_seed)  # noqa: S311  # nosec B311
    created = _seed_appointments(db, service, patients, rng, busy_days=busy)
    db.commit()
    return created


def main() -> None:
    from app.db.session import SessionLocal

    if "--refresh-appointments" in sys.argv:
        with SessionLocal() as db:
            created = refresh_appointments(db)
        print(f"Demo appointments added for the next {APPOINTMENT_DAYS} days: {created}.")
        return

    staff_password = _require_password("SEED_STAFF_PASSWORD")
    patient_password = _require_password("SEED_PATIENT_PASSWORD")
    with SessionLocal() as db:
        if seed(db, staff_password, patient_password):
            print(
                "Demo data created: 6 therapists, 2 front desk, 1 admin, 5 services, 50 patients."
            )
        else:
            print("Demo data already exists; nothing changed.")


if __name__ == "__main__":
    main()
