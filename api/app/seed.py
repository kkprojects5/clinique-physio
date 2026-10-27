"""Demo data for development and the demo deployment (D1).

Creates 6 therapists with weekly schedules, 2 front-desk agents, 1 admin,
5 services, 50 fictional patients and some confirmed appointments.

All people are fictional. Emails use example.com and phone numbers use 555,
both reserved for examples, so no real person can be reached.

Run from the api folder:
    python -m app.seed

Passwords are read from SEED_STAFF_PASSWORD and SEED_PATIENT_PASSWORD (.env).
They are never written in the code or the README (spec 7.3).
"""

import os
import random
import sys
from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import Range
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.crypto import encrypt
from app.core.security import hash_password
from app.models import (
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
from app.services.slots import BUFFER_MINUTES

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

    _seed_appointments(db, services["f30"], patients, rng)
    db.commit()
    return True


def _seed_appointments(db: Session, service: Service, patients: list, rng: random.Random) -> None:
    """Book about a third of the free 30-min slots of the next 2 weeks, never overlapping."""
    start = availability_service.today_local() + timedelta(days=1)
    slots = availability_service.find_slots(db, service.id, None, start, start + timedelta(days=13))
    last_end: dict = {}
    buffer = timedelta(minutes=BUFFER_MINUTES)
    for slot in slots:
        previous_end = last_end.get(slot.therapist_id)
        if previous_end is not None and slot.period.start < previous_end + buffer:
            continue
        if rng.random() > 0.35:
            continue
        patient, user = rng.choice(patients)
        db.add(
            Appointment(
                patient_id=patient.id,
                therapist_id=slot.therapist_id,
                service_id=service.id,
                during=Range(slot.period.start, slot.period.end),
                status="confirmed",
                created_by=user.id,
            )
        )
        last_end[slot.therapist_id] = slot.period.end
    db.flush()


def main() -> None:
    from app.db.session import SessionLocal

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
