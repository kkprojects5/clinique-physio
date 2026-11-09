"""Shapes for schedules (front desk) and a patient's own appointments."""

import uuid
from datetime import date, datetime

from pydantic import BaseModel


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
