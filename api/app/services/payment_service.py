"""Deposit payment with Stripe (B-BKG-04) and refunds (B-BKG-06).

1. The patient asks to pay a held appointment: we create (or reuse) a Stripe PaymentIntent for
   the deposit. The appointment becomes 'pending_payment' and gets 10 more minutes, once.
2. Stripe sends a signed webhook. Each event is recorded once (unique Stripe event id), so a
   repeated event changes nothing. 'payment_intent.succeeded' confirms the appointment.
3. If the payment arrives after the hold expired, or after a cancellation, the deposit is
   refunded automatically: the patient never pays for an appointment they do not have.
4. A cancellation more than 24 hours before refunds the deposit through Stripe.
"""

import uuid
from datetime import UTC, datetime, timedelta

from psycopg.errors import UniqueViolation
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import UNPAID_STATUSES, Appointment, Patient, Payment, PaymentEvent, Service, User
from app.services.booking_service import HOLD_MINUTES, BookingError, NotFound, record
from app.services.stripe_gateway import PaymentError, StripeGateway, WebhookEvent


class PaymentsDisabled(BookingError):
    status_code = 503

    def __init__(self) -> None:
        super().__init__("Online payment is not available right now. Please call the clinic.")


class PaymentFailed(BookingError):
    status_code = 502


def _deposit(db: Session, appointment_id: uuid.UUID, statuses: tuple[str, ...]) -> Payment | None:
    return db.scalar(
        select(Payment)
        .where(
            Payment.appointment_id == appointment_id,
            Payment.type == "deposit",
            Payment.status.in_(statuses),
        )
        .order_by(Payment.created_at.desc())
        .limit(1)
    )


def start_deposit(
    db: Session,
    patient: Patient,
    user: User,
    appointment_id: uuid.UUID,
    gateway: StripeGateway,
    now: datetime | None = None,
) -> tuple[Appointment, Payment, str]:
    """Returns (appointment, payment, client secret for Stripe's card form)."""
    if not gateway.enabled:
        raise PaymentsDisabled
    moment = now or datetime.now(UTC)
    appointment = db.scalar(
        select(Appointment)
        .where(Appointment.id == appointment_id, Appointment.patient_id == patient.id)
        .with_for_update()
    )
    if appointment is None:
        raise NotFound
    if appointment.status not in UNPAID_STATUSES:
        db.rollback()
        raise BookingError("This appointment does not need a deposit payment.")
    if appointment.hold_expires_at is None or appointment.hold_expires_at <= moment:
        db.rollback()
        raise BookingError("The 10 minutes to pay have passed. Please choose a time again.")

    payment = _deposit(db, appointment.id, ("pending", "failed"))
    try:
        if payment is not None and payment.stripe_id:
            intent = gateway.retrieve_intent(payment.stripe_id)
            payment.status = "pending"
        else:
            service = db.get(Service, appointment.service_id)
            intent = gateway.create_deposit_intent(
                service.deposit_cents, str(appointment.id), f"deposit-{appointment.id}"
            )
            payment = Payment(
                appointment_id=appointment.id,
                amount_cents=service.deposit_cents,
                type="deposit",
                method="stripe",
                status="pending",
                stripe_id=intent.id,
            )
            db.add(payment)
    except PaymentError as error:
        db.rollback()
        raise PaymentFailed(f"Payment could not be started: {error}") from error

    if appointment.status == "held":
        # One extension only, so a slot cannot be blocked for ever.
        appointment.hold_expires_at = moment + timedelta(minutes=HOLD_MINUTES)
        record(db, appointment, "pending_payment", user.id, "deposit payment started")
    payment.updated_at = moment
    db.commit()
    return appointment, payment, intent.client_secret


def handle_event(db: Session, event: WebhookEvent, gateway: StripeGateway) -> str:
    """Apply a verified Stripe event once. Returns what was done (for logs and tests)."""
    db.add(PaymentEvent(stripe_event_id=event.id, event_type=event.type))
    try:
        db.flush()
    except IntegrityError as error:
        db.rollback()
        if isinstance(error.orig, UniqueViolation):
            return "duplicate"
        raise
    stored = db.scalar(select(PaymentEvent).where(PaymentEvent.stripe_event_id == event.id))

    outcome = "ignored"
    if event.type in ("payment_intent.succeeded", "payment_intent.payment_failed"):
        payment = db.scalar(
            select(Payment).where(Payment.stripe_id == event.object_id).with_for_update()
        )
        if payment is not None:
            stored.payment_id = payment.id
            if event.type == "payment_intent.payment_failed":
                payment.status = "failed"
                outcome = "failed"
            else:
                outcome = _paid(db, payment, gateway)
            payment.updated_at = datetime.now(UTC)
    stored.processed_at = datetime.now(UTC)
    db.commit()
    return outcome


def _paid(db: Session, payment: Payment, gateway: StripeGateway) -> str:
    payment.status = "succeeded"
    appointment = db.scalar(
        select(Appointment).where(Appointment.id == payment.appointment_id).with_for_update()
    )
    if appointment.status in UNPAID_STATUSES:
        appointment.hold_expires_at = None
        record(db, appointment, "confirmed", None, "deposit paid")
        return "confirmed"
    # Paid too late (hold expired) or after a cancellation: give the money back.
    _refund(db, payment, gateway, f"refund-late-{payment.id}")
    return "refunded"


def _refund(db: Session, payment: Payment, gateway: StripeGateway, key: str) -> Payment:
    refund_id, status = gateway.refund(payment.stripe_id, key)
    refund = Payment(
        appointment_id=payment.appointment_id,
        amount_cents=payment.amount_cents,
        type="refund",
        method="stripe",
        status="succeeded" if status == "succeeded" else "pending",
        stripe_id=refund_id,
    )
    db.add(refund)
    return refund


def refund_deposit(db: Session, appointment: Appointment, gateway: StripeGateway) -> None:
    """Refund the paid deposit of an appointment (used when cancelling more than 24 h before).

    Demo appointments created without an online payment have nothing to refund.
    """
    payment = _deposit(db, appointment.id, ("succeeded",))
    if payment is None or not payment.stripe_id:
        return
    already = db.scalar(
        select(Payment).where(Payment.appointment_id == appointment.id, Payment.type == "refund")
    )
    if already is not None:
        return
    try:
        _refund(db, payment, gateway, f"refund-{appointment.id}")
    except PaymentError as error:
        raise PaymentFailed(
            "The refund could not be made right now, so nothing was cancelled. Please try again."
        ) from error
