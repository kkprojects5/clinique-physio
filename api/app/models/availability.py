"""Therapist working hours and exceptions (B-AVL-02).

Rules use local clock time (America/Toronto): "Monday 8:00" stays 8:00
on both sides of a daylight-saving change.
"""

import uuid
from datetime import time

from sqlalchemy import CheckConstraint, ForeignKey, SmallInteger, Text, text
from sqlalchemy.dialects.postgresql import TSTZRANGE, UUID, Range
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AvailabilityRule(Base):
    __tablename__ = "availability_rules"
    __table_args__ = (
        CheckConstraint("weekday BETWEEN 1 AND 7", name="ck_availability_rules_weekday"),
        CheckConstraint("start_time < end_time", name="ck_availability_rules_times"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    therapist_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("therapists.id"), index=True)
    weekday: Mapped[int] = mapped_column(SmallInteger)  # 1 = Monday ... 7 = Sunday
    start_time: Mapped[time]
    end_time: Mapped[time]


class AvailabilityException(Base):
    __tablename__ = "availability_exceptions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    therapist_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("therapists.id"), index=True)
    during: Mapped[Range] = mapped_column(TSTZRANGE)
    reason: Mapped[str | None] = mapped_column(Text)
