"""Booking by patients: hold a slot, cancel, reschedule (B-BKG-01 to 06).

Rules
- A patient can only hold a time that the clinic really offers (same computation as the public
  slot search), never in the past and at most 60 days ahead.
- A hold keeps the slot 10 minutes while the deposit is paid (B-BKG-03). After that it becomes
  'expired' and the slot is free again. A new hold by the same patient replaces their unpaid one,
  so nobody can block many slots.
- The database guarantees no double booking (ADR-001). If two patients take the same slot at the
  same moment, the second gets SlotUnavailable (HTTP 409).
- A first treatment needs an initial evaluation before it.
- Cancel or reschedule more than 24 real hours before the start: the deposit is refunded.
  Less than 24 hours: cancelling keeps the deposit as a fee, and rescheduling is refused
  (BR-4). 24 hours are counted in UTC, so a daylight saving change does not shift the limit.
- Every status change is written to appointment_status_history with who made it (B-BKG-05).
"""

import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from psycopg.errors import ExclusionViolation
from sqlalchemy import exists, func, select
from sqlalchemy.dialects.postgresql import Range
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, aliased

from app.db.locks import lock_therapist_schedule
from app.db.retry import retry_on_deadlock
from app.models import (
    UNPAID_STATUSES,
    Appointment,
    AppointmentStatusHistory,
    Patient,
    Service,
    User,
)
from app.services import availability_service
from app.services.slots import CLINIC_TZ

HOLD_MINUTES = 10
FREE_CHANGE_HOURS = 24
CHANGEABLE = ("held", "pending_payment", "confirmed")
EVALUATION_DONE = ("confirmed", "checked_in", "completed")


class BookingError(Exception):
    """A booking rule refused the request. The message is safe to show to the patient."""

    status_code = 409


class SlotUnavailable(BookingError):
    def __init__(self) -> None:
        super().__init__("This time is no longer available. Please choose another one.")


class NotFound(BookingError):
    status_code = 404

    def __init__(self, what: str = "Appointment not found.") -> None:
        super().__init__(what)


class InvalidRequest(BookingError):
    status_code = 422


def record(
    db: Session,
    appointment: Appointment,
    to_status: str,
    actor: uuid.UUID | None,
    reason: str | None = None,
) -> None:
    """Change the status and keep a history row. actor None means the system."""
    db.add(
        AppointmentStatusHistory(
            appointment_id=appointment.id,
            from_status=appointment.status if appointment.id else None,
            to_status=to_status,
            changed_by=actor,
            reason=reason,
        )
    )
    appointment.status = to_status
    appointment.version = (appointment.version or 1) + 1
    appointment.updated_at = datetime.now(UTC)


def release_expired_holds(db: Session, now: datetime) -> int:
    """Turn unpaid holds whose 10 minutes have passed into 'expired'. Returns how many."""
    stale = db.scalars(
        select(Appointment)
        .where(Appointment.status.in_(UNPAID_STATUSES), Appointment.hold_expires_at < now)
        .with_for_update(skip_locked=True)
    ).all()
    for appointment in stale:
        record(db, appointment, "expired", None, "deposit not paid within 10 minutes")
    db.flush()
    return len(stale)


def _own(db: Session, patient: Patient, appointment_id: uuid.UUID) -> Appointment:
    """The patient's own appointment, locked for the change. Others' look like 'not found'."""
    appointment = db.scalar(
        select(Appointment)
        .where(Appointment.id == appointment_id, Appointment.patient_id == patient.id)
        .with_for_update()
    )
    if appointment is None:
        raise NotFound
    return appointment


def _offered_slot(
    db: Session,
    service_id: uuid.UUID,
    therapist_id: uuid.UUID | None,
    start: datetime,
) -> uuid.UUID:
    """Therapist of an offered slot starting exactly at 'start' (first available if no choice)."""
    if start.tzinfo is None:
        raise InvalidRequest("start must include a time zone, e.g. 2026-11-20T10:00:00-05:00")
    day = start.astimezone(CLINIC_TZ).date()
    try:
        slots = availability_service.find_slots(db, service_id, therapist_id, day, day)
    except availability_service.InvalidSearch:
        raise NotFound("Service not found.") from None
    for slot in slots:
        if slot.period.start == start:
            return slot.therapist_id
    raise SlotUnavailable


def _needs_evaluation(db: Session, patient: Patient, service: Service, start: datetime) -> bool:
    """A treatment needs an initial evaluation (confirmed or done) before it."""
    if service.is_initial_evaluation:
        return False
    evaluation = aliased(Service)
    has_one = db.scalar(
        select(
            exists()
            .where(
                Appointment.patient_id == patient.id,
                Appointment.status.in_(EVALUATION_DONE),
                func.lower(Appointment.during) < start,
            )
            .where(Appointment.service_id == evaluation.id, evaluation.is_initial_evaluation)
        )
    )
    return not has_one


def _in_transaction(db: Session, work):
    """Run work() and commit, or undo everything. The no-overlap rule becomes SlotUnavailable."""
    try:
        return retry_on_deadlock(db, work)
    except IntegrityError as error:
        db.rollback()
        if isinstance(error.orig, ExclusionViolation):
            raise SlotUnavailable from None
        raise
    except BookingError:
        db.rollback()  # nothing of a refused request is kept (not even released holds)
        raise


def hold(
    db: Session,
    patient: Patient,
    user: User,
    service_id: uuid.UUID,
    therapist_id: uuid.UUID | None,
    start: datetime,
    now: datetime | None = None,
) -> Appointment:
    """Keep a slot 10 minutes for this patient while they pay the deposit."""

    def work() -> Appointment:
        moment = now or datetime.now(UTC)
        release_expired_holds(db, moment)
        # A new hold replaces this patient's unpaid hold: one slot at a time.
        for previous in db.scalars(
            select(Appointment)
            .where(Appointment.patient_id == patient.id, Appointment.status == "held")
            .with_for_update()
        ):
            record(db, previous, "expired", user.id, "replaced by a new hold")
        db.flush()

        service = db.get(Service, service_id)
        if service is None or not service.is_active:
            raise NotFound("Service not found.")
        chosen = _offered_slot(db, service_id, therapist_id, start)
        lock_therapist_schedule(db, chosen)  # competing bookings take turns (ADR-001)
        if _needs_evaluation(db, patient, service, start):
            raise BookingError(
                "A first treatment needs an initial evaluation before it. "
                "Please book an initial evaluation first."
            )
        appointment = Appointment(
            id=uuid.uuid4(),
            patient_id=patient.id,
            therapist_id=chosen,
            service_id=service.id,
            during=Range(start, start + timedelta(minutes=service.duration_min)),
            status="held",
            hold_expires_at=moment + timedelta(minutes=HOLD_MINUTES),
            created_by=user.id,
        )
        db.add(appointment)
        db.add(
            AppointmentStatusHistory(
                appointment_id=appointment.id,
                from_status=None,
                to_status="held",
                changed_by=user.id,
                reason="booked online",
            )
        )
        db.flush()  # the database checks the no-overlap rule here
        return appointment

    return _in_transaction(db, work)


def refund_due(appointment: Appointment, now: datetime) -> bool:
    """Deposit refunded only for a paid appointment changed more than 24 real hours ahead."""
    return appointment.status == "confirmed" and appointment.during.lower - now > timedelta(
        hours=FREE_CHANGE_HOURS
    )


def cancel(
    db: Session,
    patient: Patient,
    user: User,
    appointment_id: uuid.UUID,
    now: datetime | None = None,
    refund: Callable[[Appointment], None] | None = None,
) -> tuple[Appointment, bool]:
    """Cancel the patient's own appointment. Returns (appointment, deposit refunded).

    refund(appointment) gives the deposit back (Stripe); it runs before the cancellation is
    saved, so a failed refund cancels nothing and the patient can try again.
    """
    moment = now or datetime.now(UTC)
    appointment = _own(db, patient, appointment_id)
    if appointment.status not in CHANGEABLE or appointment.during.lower <= moment:
        db.rollback()
        raise BookingError("This appointment can no longer be cancelled online.")
    refunded = refund_due(appointment, moment)
    if appointment.status == "confirmed":
        reason = (
            "deposit refunded"
            if refunded
            else f"deposit kept: less than {FREE_CHANGE_HOURS} hours before"
        )
    else:
        reason = "cancelled before payment"
    if refunded and refund is not None:
        try:
            refund(appointment)
        except BookingError:
            db.rollback()
            raise
    record(db, appointment, "cancelled_by_patient", user.id, reason)
    db.commit()
    return appointment, refunded


def reschedule(
    db: Session,
    patient: Patient,
    user: User,
    appointment_id: uuid.UUID,
    new_start: datetime,
    therapist_id: uuid.UUID | None = None,
    now: datetime | None = None,
) -> Appointment:
    """Move a paid appointment to another offered time, more than 24 hours ahead."""
    moment = now or datetime.now(UTC)

    def work() -> Appointment:
        appointment = _own(db, patient, appointment_id)
        if appointment.status != "confirmed":
            raise BookingError("Only a confirmed appointment can be rescheduled.")
        if not refund_due(appointment, moment):
            raise BookingError(
                f"Less than {FREE_CHANGE_HOURS} hours before the appointment, it can no longer "
                "be changed online. Please call the clinic."
            )
        release_expired_holds(db, moment)
        chosen = _offered_slot(
            db, appointment.service_id, therapist_id or appointment.therapist_id, new_start
        )
        lock_therapist_schedule(db, chosen)  # competing bookings take turns (ADR-001)
        old = appointment.during.lower.astimezone(CLINIC_TZ).strftime("%Y-%m-%d %H:%M")
        length = appointment.during.upper - appointment.during.lower
        appointment.during = Range(new_start, new_start + length)
        appointment.therapist_id = chosen
        record(db, appointment, "confirmed", user.id, f"rescheduled from {old}")
        db.flush()  # the database checks the no-overlap rule here
        return appointment

    return _in_transaction(db, work)
