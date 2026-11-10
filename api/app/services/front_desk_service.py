"""Front desk: find a patient, check-in and no-show (B-FRD-02, B-FRD-03).

Booking, moving and cancelling by phone reuse the booking rules (booking_service), so the desk
and the website can never disagree. Every status change keeps who made it (status history).
"""

import re
import uuid
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import Appointment, Patient, User
from app.services.booking_service import BookingError, locked_appointment, record
from app.services.slots import CLINIC_TZ

SEARCH_LIMIT = 20
NO_SHOW_AFTER = timedelta(minutes=15)


def search_patients(db: Session, query: str) -> list[Patient]:
    """By date of birth (2026-01-31), phone digits (at least 4) or name (each word)."""
    text = query.strip()
    if len(text) < 2:
        raise BookingError("Type at least 2 characters.")
    statement = select(Patient)
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        try:
            statement = statement.where(Patient.date_of_birth == date.fromisoformat(text))
        except ValueError:
            return []
    elif len(digits := re.sub(r"\D", "", text)) >= 4 and not re.search(r"[A-Za-zÀ-ÿ]", text):
        phone_digits = func.regexp_replace(Patient.phone, r"\D", "", "g")
        statement = statement.where(phone_digits.contains(digits))
    else:
        # Wildcards typed by the user are removed, so "%" cannot match every patient.
        words = [w for w in (re.sub(r"[%_\\]", "", w) for w in text.split()[:3]) if len(w) >= 2]
        if not words:
            return []
        for word in words:
            pattern = f"%{word}%"
            statement = statement.where(
                or_(Patient.first_name.ilike(pattern), Patient.last_name.ilike(pattern))
            )
    return list(
        db.scalars(statement.order_by(Patient.last_name, Patient.first_name).limit(SEARCH_LIMIT))
    )


def check_in(
    db: Session, actor: User, appointment_id: uuid.UUID, now: datetime | None = None
) -> Appointment:
    """The patient has arrived: only on the day of the appointment."""
    moment = now or datetime.now(UTC)
    appointment = locked_appointment(db, appointment_id)
    if appointment.status != "confirmed":
        db.rollback()
        raise BookingError("Only a confirmed appointment can be checked in.")
    if appointment.during.lower.astimezone(CLINIC_TZ).date() != moment.astimezone(CLINIC_TZ).date():
        db.rollback()
        raise BookingError("A patient can only be checked in on the day of the appointment.")
    record(db, appointment, "checked_in", actor.id, "arrived at the desk")
    db.commit()
    return appointment


def mark_no_show(
    db: Session, actor: User, appointment_id: uuid.UUID, now: datetime | None = None
) -> Appointment:
    """The patient did not come: possible 15 minutes after the start (B-FRD-03).

    The deposit is kept as a fee, like a late cancellation (BR-4)."""
    moment = now or datetime.now(UTC)
    appointment = locked_appointment(db, appointment_id)
    if appointment.status != "confirmed":
        db.rollback()
        raise BookingError("Only a confirmed appointment can be marked as a no-show.")
    if moment < appointment.during.lower + NO_SHOW_AFTER:
        db.rollback()
        raise BookingError("A no-show can be recorded 15 minutes after the start.")
    record(db, appointment, "no_show", actor.id, "did not come; deposit kept")
    db.commit()
    return appointment
