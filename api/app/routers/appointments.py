"""Online booking by patients: hold, cancel, reschedule (B-BKG-01 to 06).

Payment of the deposit (Stripe) confirms a held appointment; it is added in the next step.
"""

import uuid

from fastapi import APIRouter, HTTPException, Request, status

from app.core import rate_limit
from app.core.rate_limit import limiter
from app.dependencies import CurrentPatient, CurrentUser, DbSession
from app.models import Appointment, Service, Therapist
from app.schemas.schedule import (
    BookingOut,
    CancelOut,
    HoldRequest,
    RescheduleRequest,
    ServiceRef,
    TherapistRef,
)
from app.services import booking_service
from app.services.slots import CLINIC_TZ

router = APIRouter(prefix="/appointments", tags=["booking"])


def _out(db: DbSession, appointment: Appointment) -> BookingOut:
    service = db.get(Service, appointment.service_id)
    therapist = db.get(Therapist, appointment.therapist_id)
    return BookingOut(
        id=appointment.id,
        status=appointment.status,
        start=appointment.during.lower,
        end=appointment.during.upper,
        start_local=appointment.during.lower.astimezone(CLINIC_TZ).isoformat(),
        hold_expires_at=appointment.hold_expires_at,
        deposit_cents=service.deposit_cents,
        service=ServiceRef(
            id=service.id,
            name_fr=service.name_fr,
            name_en=service.name_en,
            duration_min=service.duration_min,
        ),
        therapist=TherapistRef(
            id=therapist.id, first_name=therapist.first_name, last_name=therapist.last_name
        ),
    )


def _refused(error: booking_service.BookingError) -> HTTPException:
    return HTTPException(status_code=error.status_code, detail=str(error))


@router.post("/hold", status_code=status.HTTP_201_CREATED)
@limiter.limit(rate_limit.BOOKING_LIMIT)
def hold_slot(
    request: Request, data: HoldRequest, db: DbSession, user: CurrentUser, patient: CurrentPatient
) -> BookingOut:
    """Keep a free slot 10 minutes while the deposit is paid. 409 if it was just taken."""
    try:
        appointment = booking_service.hold(
            db, patient, user, data.service_id, data.therapist_id, data.start
        )
    except booking_service.BookingError as error:
        raise _refused(error) from None
    return _out(db, appointment)


@router.post("/{appointment_id}/cancel")
@limiter.limit(rate_limit.BOOKING_LIMIT)
def cancel_appointment(
    request: Request,
    appointment_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    patient: CurrentPatient,
) -> CancelOut:
    """Cancel my appointment. Deposit refunded only more than 24 hours before."""
    try:
        appointment, refunded = booking_service.cancel(db, patient, user, appointment_id)
    except booking_service.BookingError as error:
        raise _refused(error) from None
    return CancelOut(appointment=_out(db, appointment), deposit_refunded=refunded)


@router.post("/{appointment_id}/reschedule")
@limiter.limit(rate_limit.BOOKING_LIMIT)
def reschedule_appointment(
    request: Request,
    appointment_id: uuid.UUID,
    data: RescheduleRequest,
    db: DbSession,
    user: CurrentUser,
    patient: CurrentPatient,
) -> BookingOut:
    """Move my confirmed appointment to another free time, more than 24 hours ahead."""
    try:
        appointment = booking_service.reschedule(
            db, patient, user, appointment_id, data.start, data.therapist_id
        )
    except booking_service.BookingError as error:
        raise _refused(error) from None
    return _out(db, appointment)
