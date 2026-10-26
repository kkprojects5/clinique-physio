"""Patient profile. Minimal data only (B-AUTH-01, NFR-06)."""

import uuid
from datetime import date, datetime

from sqlalchemy import ForeignKey, LargeBinary, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), unique=True)
    first_name: Mapped[str] = mapped_column(Text)
    last_name: Mapped[str] = mapped_column(Text)
    date_of_birth: Mapped[date]
    phone: Mapped[str] = mapped_column(Text)
    emergency_contact_enc: Mapped[bytes | None] = mapped_column(LargeBinary)  # encrypted
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
