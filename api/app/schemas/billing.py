import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel


class PaymentLine(BaseModel):
    type: str  # deposit, balance or refund
    method: str  # stripe, cash, debit or credit
    amount_cents: int
    paid_at: datetime


class BillingOut(BaseModel):
    """What the appointment costs, what was paid and what is left (all in cents)."""

    appointment_id: uuid.UUID
    status: str
    price_cents: int
    paid_cents: int
    due_cents: int
    can_pay: bool  # the patient came and something is left to pay
    receipt_available: bool
    receipt_number: str
    payments: list[PaymentLine]


class ReceiptRef(BaseModel):
    """A past visit that has a receipt (B-BKG-10)."""

    appointment_id: uuid.UUID
    start: datetime
    service_fr: str
    service_en: str
    therapist: str
    paid_cents: int
    receipt_number: str


class DeskPaymentIn(BaseModel):
    """The amount is never sent: the server computes the balance."""

    method: Literal["cash", "debit", "credit"]


class TherapistWeekOut(BaseModel):
    therapist_id: uuid.UUID
    first_name: str
    last_name: str
    appointments: int
    seen: int
    no_shows: int
    booked_minutes: int
    working_minutes: int
    occupancy: float | None  # 0 to 1; empty when the therapist has no working hours


class WeekReportOut(BaseModel):
    week_start: date
    week_end: date
    appointments: int
    seen: int
    no_shows: int
    cancelled_by_patient: int
    cancelled_by_clinic: int
    confirmed: int  # booked, not happened yet
    no_show_rate: float | None
    occupancy: float | None
    revenue_cents: int
    deposits_cents: int
    desk_cents: int
    refunds_cents: int
    therapists: list[TherapistWeekOut]
