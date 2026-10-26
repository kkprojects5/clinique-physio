"""Service catalog and which therapist provides which service (B-AVL-01)."""

import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Service(Base):
    __tablename__ = "services"
    __table_args__ = (
        CheckConstraint("duration_min IN (30, 45, 60)", name="ck_services_duration"),
        CheckConstraint("price_cents >= 0", name="ck_services_price"),
        CheckConstraint(
            "deposit_cents >= 0 AND deposit_cents <= price_cents", name="ck_services_deposit"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    name_fr: Mapped[str] = mapped_column(Text)
    name_en: Mapped[str] = mapped_column(Text)
    description_fr: Mapped[str | None] = mapped_column(Text)
    description_en: Mapped[str | None] = mapped_column(Text)
    duration_min: Mapped[int]
    price_cents: Mapped[int]  # money in cents, never floating point
    deposit_cents: Mapped[int]
    is_initial_evaluation: Mapped[bool] = mapped_column(server_default=text("false"))
    is_active: Mapped[bool] = mapped_column(server_default=text("true"))


class TherapistService(Base):
    """Many-to-many link between therapists and services."""

    __tablename__ = "therapist_services"

    therapist_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("therapists.id"), primary_key=True
    )
    service_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("services.id"), primary_key=True)
