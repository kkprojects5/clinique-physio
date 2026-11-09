"""Payments and Stripe webhook events (B-BKG-04, B-BKG-06)."""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

PAYMENT_TYPES = ("deposit", "refund")
PAYMENT_STATUSES = ("pending", "succeeded", "failed")


class Payment(Base):
    """Money for an appointment: a deposit paid online, or a refund of it.

    Card details never reach our systems: Stripe handles them. We keep only the amount,
    the status and Stripe's identifier.
    """

    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint("amount_cents > 0", name="ck_payments_amount"),
        CheckConstraint("type IN ('deposit', 'refund')", name="ck_payments_type"),
        CheckConstraint("method IN ('stripe', 'cash', 'debit')", name="ck_payments_method"),
        CheckConstraint("status IN ('pending', 'succeeded', 'failed')", name="ck_payments_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    appointment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("appointments.id"), index=True)
    amount_cents: Mapped[int]
    type: Mapped[str] = mapped_column(Text)
    method: Mapped[str] = mapped_column(Text, server_default=text("'stripe'"))
    status: Mapped[str] = mapped_column(Text)
    stripe_id: Mapped[str | None] = mapped_column(Text, unique=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now())


class PaymentEvent(Base):
    """Each Stripe webhook event, recorded once: a repeated event is ignored (idempotency).

    Only the event id and type are kept, not Stripe's full payload (data minimization).
    """

    __tablename__ = "payment_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    payment_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("payments.id"))
    stripe_event_id: Mapped[str] = mapped_column(Text, unique=True)
    event_type: Mapped[str] = mapped_column(Text)
    received_at: Mapped[datetime] = mapped_column(server_default=func.now())
    processed_at: Mapped[datetime | None]
