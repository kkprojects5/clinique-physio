"""Shapes for schedules (front desk) and a patient's own appointments."""

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


class TherapistRef(BaseModel):
    id: uuid.UUID
    first_name: str
    last_name: str


class PatientRef(BaseModel):
    """What the front desk needs to recognise and call a patient. No clinical data (B-CLN-05)."""

    id: uuid.UUID
    first_name: str
    last_name: str
    phone: str


class ServiceRef(BaseModel):
    id: uuid.UUID
    name_fr: str
    name_en: str
    duration_min: int


class DeskAppointment(BaseModel):
    id: uuid.UUID
    therapist_id: uuid.UUID
    start: datetime
    end: datetime
    start_local: str
    status: str
    service: ServiceRef
    patient: PatientRef


class DaySchedule(BaseModel):
    date: date
    therapists: list[TherapistRef]
    appointments: list[DeskAppointment]


class MyAppointment(BaseModel):
    id: uuid.UUID
    start: datetime
    end: datetime
    start_local: str
    status: str
    service: ServiceRef
    therapist: TherapistRef


class HoldRequest(BaseModel):
    service_id: uuid.UUID
    therapist_id: uuid.UUID | None = None  # empty: first available therapist
    start: datetime  # with time zone, exactly as returned by GET /availability


class RescheduleRequest(BaseModel):
    start: datetime
    therapist_id: uuid.UUID | None = None  # empty: same therapist


class BookingOut(BaseModel):
    id: uuid.UUID
    status: str
    start: datetime
    end: datetime
    start_local: str
    hold_expires_at: datetime | None
    deposit_cents: int
    service: ServiceRef
    therapist: TherapistRef


class CancelOut(BaseModel):
    appointment: BookingOut
    deposit_refunded: bool  # True: cancelled more than 24 hours before a paid appointment


class PaymentStart(BaseModel):
    """What the website needs to show Stripe's card form."""

    appointment: BookingOut
    payment_id: uuid.UUID
    client_secret: str  # given to Stripe.js only; never logged
    publishable_key: str
    amount_cents: int
    currency: str


class PatientFound(BaseModel):
    """A search result for the front desk: what is needed to recognize the caller."""

    id: uuid.UUID
    first_name: str
    last_name: str
    date_of_birth: date
    phone: str


class DeskBookingIn(BaseModel):
    patient_id: uuid.UUID
    service_id: uuid.UUID
    therapist_id: uuid.UUID | None = None  # empty: first available therapist
    start: datetime  # with time zone, as returned by GET /availability


class SyncAction(BaseModel):
    """An action the desk recorded while the API could not be reached (challenge B-C5)."""

    id: uuid.UUID  # made by the desktop app, to match the result to the action
    appointment_id: uuid.UUID
    action: Literal["check_in", "no_show"]
    seen_status: str = Field(max_length=40)  # the status the desk saw when it acted
    done_at: datetime  # when the desk clicked, offline


class SyncRequest(BaseModel):
    actions: list[SyncAction] = Field(min_length=1, max_length=100)


class SyncResult(BaseModel):
    """applied: done now. already_done: nothing to do. conflict: the appointment changed while
    the desk was offline; the server's state is kept. refused: a rule says no (too early...)."""

    id: uuid.UUID
    appointment_id: uuid.UUID
    result: Literal["applied", "already_done", "conflict", "refused"]
    status: str | None  # the appointment's status now
    detail: str | None = None
