"""Front desk: find a patient, check-in and no-show (B-FRD-02, B-FRD-03), and the
synchronization of actions recorded offline by the desktop app (challenge B-C5).

Booking, moving and cancelling by phone reuse the booking rules (booking_service), so the desk
and the website can never disagree. Every status change keeps who made it (status history).
"""

import re
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from fastapi import Request
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import Appointment, Patient, User
from app.services import audit_service
from app.services.booking_service import BookingError, NotFound, locked_appointment, record
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


# --- Offline synchronization (challenge B-C5) -----------------------------------------------
#
# When the API cannot be reached, the desktop app keeps the desk's check-ins and no-shows in
# memory (never on disk: no patient data is stored on the computer) and sends them here when
# the connection returns. Rule, documented in docs/challenges.md:
#
#   The server's state wins. An offline action is applied only if the appointment is still in
#   the status the desk saw when it acted. If it changed meanwhile (the patient cancelled
#   online, a colleague acted, the clinic cancelled), the action is NOT applied: the desk gets
#   a conflict with the current status and handles it with the patient (rebook if they are
#   here). Every conflict is written in the audit log.
#
# The time rules still apply, using the moment the desk clicked: a check-in only on the day of
# the appointment, a no-show only 15 minutes after the start. An action older than 12 hours or
# in the future is refused.

TARGET = {"check_in": "checked_in", "no_show": "no_show"}
MAX_OFFLINE_AGE = timedelta(hours=12)


@dataclass
class SyncOutcome:
    id: uuid.UUID
    appointment_id: uuid.UUID
    result: str
    status: str | None
    detail: str | None = None


def _current_status(db: Session, appointment_id: uuid.UUID) -> str | None:
    appointment = db.get(Appointment, appointment_id, populate_existing=True)
    return appointment.status if appointment else None


def sync_offline_actions(
    db: Session,
    actor: User,
    actions: list,
    request: Request | None = None,
    now: datetime | None = None,
) -> list[SyncOutcome]:
    """Apply the desk's offline actions in the order they were done, one by one."""
    moment = now or datetime.now(UTC)
    outcomes = []
    for action in sorted(actions, key=lambda a: a.done_at):
        target = TARGET[action.action]
        current = _current_status(db, action.appointment_id)

        def outcome(result, detail=None, status=None, action=action, current=current):
            return SyncOutcome(action.id, action.appointment_id, result, status or current, detail)

        if current is None:
            outcomes.append(outcome("refused", "This appointment does not exist."))
            continue
        if current == target:
            outcomes.append(outcome("already_done"))
            continue
        if current != action.seen_status:
            appointment = db.get(Appointment, action.appointment_id)
            audit_service.log(
                db,
                actor.id,
                "sync_conflict",
                "appointment",
                appointment.id,
                appointment.patient_id,
                request,
            )
            db.commit()
            outcomes.append(
                outcome(
                    "conflict",
                    f"Changed to {current} while the desk was offline; the offline "
                    f"{action.action.replace('_', '-')} was not applied.",
                )
            )
            continue
        done_at = action.done_at.astimezone(UTC)
        if done_at > moment + timedelta(minutes=5) or moment - done_at > MAX_OFFLINE_AGE:
            outcomes.append(outcome("refused", "Recorded too long ago, or in the future."))
            continue
        try:
            apply = check_in if action.action == "check_in" else mark_no_show
            appointment = apply(db, actor, action.appointment_id, now=done_at)
        except NotFound:
            outcomes.append(outcome("refused", "This appointment does not exist."))
            continue
        except BookingError as error:
            # Changed between the check and the lock (another desk at the same moment)?
            now_status = _current_status(db, action.appointment_id)
            if now_status != action.seen_status and now_status != target:
                outcomes.append(outcome("conflict", str(error), now_status))
            else:
                outcomes.append(outcome("refused", str(error), now_status))
            continue
        outcomes.append(outcome("applied", status=appointment.status))
    return outcomes
