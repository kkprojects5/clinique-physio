"""Front-desk endpoints (desktop app). Front desk or admin, with MFA.

Day schedule (B-FRD-01); find a patient and book, move or cancel by phone (B-FRD-02);
check-in and no-show (B-FRD-03). Never any clinical information.
"""

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.core import rate_limit
from app.core.rate_limit import limiter
from app.dependencies import DbSession, FrontDeskUser
from app.models import Appointment, Patient, Service
from app.routers.appointments import _out as booking_out
from app.schemas.schedule import (
    CancelOut,
    DaySchedule,
    DeskAppointment,
    DeskBookingIn,
    PatientFound,
    PatientRef,
    RescheduleRequest,
    ServiceRef,
    TherapistRef,
)
from app.services import booking_service, front_desk_service, payment_service, schedule_service
from app.services.slots import CLINIC_TZ
from app.services.stripe_gateway import StripeGateway, get_gateway

router = APIRouter(prefix="/desk", tags=["front desk"])
Gateway = Annotated[StripeGateway, Depends(get_gateway)]


@router.get("/schedule")
def read_day_schedule(
    day: Annotated[date, Query(alias="date")], db: DbSession, _: FrontDeskUser
) -> DaySchedule:
    """Every therapist's appointments for one day (?date=2026-11-02, Montréal time)."""
    therapists, rows = schedule_service.day_schedule(db, day)
    return DaySchedule(
        date=day,
        therapists=[
            TherapistRef(id=t.id, first_name=t.first_name, last_name=t.last_name)
            for t in therapists
        ],
        appointments=[
            DeskAppointment(
                id=a.id,
                therapist_id=a.therapist_id,
                start=a.during.lower,
                end=a.during.upper,
                start_local=a.during.lower.astimezone(CLINIC_TZ).isoformat(),
                status=a.status,
                service=ServiceRef(
                    id=s.id, name_fr=s.name_fr, name_en=s.name_en, duration_min=s.duration_min
                ),
                patient=PatientRef(
                    id=p.id, first_name=p.first_name, last_name=p.last_name, phone=p.phone
                ),
            )
            for a, p, s in rows
        ],
    )


def _desk_out(db: DbSession, a: Appointment) -> DeskAppointment:
    p = db.get(Patient, a.patient_id)
    s = db.get(Service, a.service_id)
    return DeskAppointment(
        id=a.id,
        therapist_id=a.therapist_id,
        start=a.during.lower,
        end=a.during.upper,
        start_local=a.during.lower.astimezone(CLINIC_TZ).isoformat(),
        status=a.status,
        service=ServiceRef(
            id=s.id, name_fr=s.name_fr, name_en=s.name_en, duration_min=s.duration_min
        ),
        patient=PatientRef(id=p.id, first_name=p.first_name, last_name=p.last_name, phone=p.phone),
    )


def _refused(error: booking_service.BookingError) -> HTTPException:
    return HTTPException(status_code=error.status_code, detail=str(error))


@router.get("/patients")
def find_patients(
    q: Annotated[str, Query(min_length=2, max_length=100)], db: DbSession, _: FrontDeskUser
) -> list[PatientFound]:
    """Find a patient by name, phone digits or date of birth (2026-01-31). At most 20."""
    try:
        found = front_desk_service.search_patients(db, q)
    except booking_service.BookingError as error:
        raise _refused(error) from None
    return [
        PatientFound(
            id=p.id,
            first_name=p.first_name,
            last_name=p.last_name,
            date_of_birth=p.date_of_birth,
            phone=p.phone,
        )
        for p in found
    ]


@router.post("/appointments", status_code=status.HTTP_201_CREATED)
@limiter.limit(rate_limit.BOOKING_LIMIT)
def book_by_phone(
    request: Request, data: DeskBookingIn, db: DbSession, desk: FrontDeskUser
) -> DeskAppointment:
    """Book for a patient on the phone: confirmed at once (paid at the clinic). 409 if taken."""
    patient = db.get(Patient, data.patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found.")
    try:
        appointment = booking_service.book_by_phone(
            db, patient, desk, data.service_id, data.therapist_id, data.start
        )
    except booking_service.BookingError as error:
        raise _refused(error) from None
    return _desk_out(db, appointment)


@router.post("/appointments/{appointment_id}/cancel")
@limiter.limit(rate_limit.BOOKING_LIMIT)
def cancel_by_phone(
    request: Request,
    appointment_id: uuid.UUID,
    db: DbSession,
    desk: FrontDeskUser,
    gateway: Gateway,
) -> CancelOut:
    """Cancel for a patient who calls. Deposit refunded only more than 24 hours before."""
    try:
        appointment, refunded = booking_service.cancel_by_phone(
            db,
            desk,
            appointment_id,
            refund=lambda a: payment_service.refund_deposit(db, a, gateway),
        )
    except booking_service.BookingError as error:
        raise _refused(error) from None
    return CancelOut(appointment=booking_out(db, appointment), deposit_refunded=refunded)


@router.post("/appointments/{appointment_id}/reschedule")
@limiter.limit(rate_limit.BOOKING_LIMIT)
def reschedule_by_phone(
    request: Request,
    appointment_id: uuid.UUID,
    data: RescheduleRequest,
    db: DbSession,
    desk: FrontDeskUser,
) -> DeskAppointment:
    """Move an appointment for a patient who calls, to another free time (any time before)."""
    try:
        appointment = booking_service.reschedule_by_phone(
            db, desk, appointment_id, data.start, data.therapist_id
        )
    except booking_service.BookingError as error:
        raise _refused(error) from None
    return _desk_out(db, appointment)


@router.post("/appointments/{appointment_id}/check-in")
def check_in(appointment_id: uuid.UUID, db: DbSession, desk: FrontDeskUser) -> DeskAppointment:
    """The patient has arrived (on the day of the appointment)."""
    try:
        appointment = front_desk_service.check_in(db, desk, appointment_id)
    except booking_service.BookingError as error:
        raise _refused(error) from None
    return _desk_out(db, appointment)


@router.post("/appointments/{appointment_id}/no-show")
def no_show(appointment_id: uuid.UUID, db: DbSession, desk: FrontDeskUser) -> DeskAppointment:
    """The patient did not come: possible 15 minutes after the start. Deposit kept."""
    try:
        appointment = front_desk_service.mark_no_show(db, desk, appointment_id)
    except booking_service.BookingError as error:
        raise _refused(error) from None
    return _desk_out(db, appointment)
