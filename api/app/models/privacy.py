"""Law 25: privacy requests and the confidentiality incident register (B-ADM-04, B-ADM-05)."""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Integer, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

REQUEST_TYPES = ("access", "correction", "deletion")
REQUEST_STATUSES = ("received", "in_progress", "completed", "refused")
RISK_LEVELS = ("low", "serious")


class PrivacyRequest(Base):
    """A person's request to see, correct or delete their information (answer within 30 days)."""

    __tablename__ = "privacy_requests"
    __table_args__ = (
        CheckConstraint("type IN ('access', 'correction', 'deletion')", name="ck_privacy_type"),
        CheckConstraint(
            "status IN ('received', 'in_progress', 'completed', 'refused')",
            name="ck_privacy_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), index=True)
    type: Mapped[str] = mapped_column(Text)
    details: Mapped[str | None] = mapped_column(Text)  # what the person asks, in their words
    status: Mapped[str] = mapped_column(Text, server_default=text("'received'"))
    requested_at: Mapped[datetime] = mapped_column(server_default=func.now())
    due_at: Mapped[datetime]
    completed_at: Mapped[datetime | None]
    handled_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    outcome: Mapped[str | None] = mapped_column(Text)  # what was done, or why it was refused


class Incident(Base):
    """Confidentiality incident register entry, kept at least 5 years (Law 25)."""

    __tablename__ = "incident_register"
    __table_args__ = (
        CheckConstraint("risk_level IN ('low', 'serious')", name="ck_incident_risk"),
        CheckConstraint("discovered_at >= occurred_at", name="ck_incident_dates"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    occurred_at: Mapped[datetime]
    discovered_at: Mapped[datetime]
    description: Mapped[str] = mapped_column(Text)
    data_categories: Mapped[str] = mapped_column(Text)
    people_affected: Mapped[int | None] = mapped_column(Integer)
    risk_level: Mapped[str] = mapped_column(Text)
    measures: Mapped[str] = mapped_column(Text)
    cai_notified_at: Mapped[datetime | None]  # Commission d'accès à l'information
    persons_notified_at: Mapped[datetime | None]
    recorded_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now())
