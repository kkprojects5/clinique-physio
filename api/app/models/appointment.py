"""Appointments, with database-level protection against double booking (B-BKG-02, B-C1).

room_id is added with the rooms table (Should, D3).
"""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Text, func, text
from sqlalchemy.dialects.postgresql import TSTZRANGE, UUID, ExcludeConstraint, Range
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# Appointment lifecycle (B-BKG-05).
APPOINTMENT_STATUSES = (
    "held",
    "pending_payment",
    "confirmed",
    "checked_in",
    "completed",
    "cancelled_by_patient",
    "cancelled_by_clinic",
    "no_show",
    "expired",  # a hold that was not paid within 10 minutes: the slot is free again
)
# Statuses that occupy the therapist's time. Cancelled or finished ones free the slot.
ACTIVE_STATUSES = ("held", "pending_payment", "confirmed", "checked_in")
# Statuses waiting for the deposit; they stop counting when hold_expires_at has passed.
UNPAID_STATUSES = ("held", "pending_payment")


class Appointment(Base):
    __tablename__ = "appointments"
    __table_args__ = (
        # A therapist cannot have two overlapping active appointments.
        # The database refuses the second one, even if both arrive at the same millisecond.
        ExcludeConstraint(
            ("therapist_id", "="),
            ("during", "&&"),
            name="ex_appointments_no_overlap",
            using="gist",
            where=text("status IN ('held', 'pending_payment', 'confirmed', 'checked_in')"),
        ),
        CheckConstraint(
            "status IN ('held', 'pending_payment', 'confirmed', 'checked_in', 'completed',"
            " 'cancelled_by_patient', 'cancelled_by_clinic', 'no_show', 'expired')",
            name="ck_appointments_status",
        ),
        CheckConstraint("NOT isempty(during)", name="ck_appointments_during"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), index=True)
    therapist_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("therapists.id"))
    service_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("services.id"))
    during: Mapped[Range[datetime]] = mapped_column(TSTZRANGE)  # stored in UTC
    status: Mapped[str] = mapped_column(Text, server_default="held")
    hold_expires_at: Mapped[datetime | None]  # 10-minute hold during payment (B-BKG-03)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    version: Mapped[int] = mapped_column(server_default=text("1"))  # offline sync conflicts
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now())


class AppointmentStatusHistory(Base):
    """Every status change, with who made it (B-BKG-05). Rows are only ever added."""

    __tablename__ = "appointment_status_history"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    appointment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("appointments.id"), index=True)
    from_status: Mapped[str | None] = mapped_column(Text)  # empty when the appointment is created
    to_status: Mapped[str] = mapped_column(Text)
    changed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))  # empty: system
    reason: Mapped[str | None] = mapped_column(Text)
    changed_at: Mapped[datetime] = mapped_column(server_default=func.now())
