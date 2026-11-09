"""Clinical tables: SOAP notes and the audit log (B-CLN-02 to 05, B-ADM-03)."""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, Identity, LargeBinary, Text, func, text
from sqlalchemy.dialects.postgresql import INET, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ClinicalNote(Base):
    """A SOAP note for one appointment. Encrypted by the API; never deleted.

    Draft (signed_at empty): the author can still edit it.
    Signed: locked for ever. A correction is a new signed note pointing to it (amends_note_id).
    """

    __tablename__ = "clinical_notes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    appointment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("appointments.id"), index=True)
    therapist_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("therapists.id"))  # author
    content_encrypted: Mapped[bytes] = mapped_column(LargeBinary)
    version: Mapped[int] = mapped_column(server_default=text("1"))
    amends_note_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("clinical_notes.id"))
    signed_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now())


class AuditLog(Base):
    """Who accessed what, when and from where. Rows can only be added (database trigger)."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    action: Mapped[str] = mapped_column(Text)
    resource_type: Mapped[str] = mapped_column(Text)
    resource_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    patient_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("patients.id"), index=True)
    ip: Mapped[str | None] = mapped_column(INET)
    client_app: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), index=True)
