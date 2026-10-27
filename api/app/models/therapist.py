"""Therapist profile (B-AVL-05)."""

import uuid

from sqlalchemy import ForeignKey, Text, text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Therapist(Base):
    __tablename__ = "therapists"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), unique=True)
    first_name: Mapped[str] = mapped_column(Text)  # shown on the public team page
    last_name: Mapped[str] = mapped_column(Text)
    licence_number: Mapped[str] = mapped_column(Text, unique=True)  # fictional
    specialties: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default="{}")
    languages: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default="{}")
    bio_fr: Mapped[str | None] = mapped_column(Text)
    bio_en: Mapped[str | None] = mapped_column(Text)
