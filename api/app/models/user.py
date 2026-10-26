"""Identity tables: users, refresh tokens and consents (B-AUTH-01, B-AUTH-02)."""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, LargeBinary, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

ROLES = ("patient", "therapist", "front_desk", "admin")


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "role IN ('patient', 'therapist', 'front_desk', 'admin')", name="ck_users_role"
        ),
        CheckConstraint("language IN ('fr', 'en')", name="ck_users_language"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    email: Mapped[str] = mapped_column(Text, unique=True)
    password_hash: Mapped[str] = mapped_column(Text)  # Argon2id, never the password
    role: Mapped[str] = mapped_column(Text)
    language: Mapped[str] = mapped_column(Text, server_default="fr")  # French by default
    mfa_secret_enc: Mapped[bytes | None] = mapped_column(LargeBinary)  # encrypted TOTP secret
    is_active: Mapped[bool] = mapped_column(server_default=text("true"))
    email_verified_at: Mapped[datetime | None]
    last_login_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class RefreshToken(Base):
    """Only a hash of the token is stored, so a database leak cannot be used to log in."""

    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(Text, unique=True)
    expires_at: Mapped[datetime]
    revoked_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class Consent(Base):
    """Which version of which consent a user gave, and when (Law 25)."""

    __tablename__ = "consents"
    __table_args__ = (
        CheckConstraint(
            "type IN ('privacy_policy', 'electronic_comms')", name="ck_consents_type"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    type: Mapped[str] = mapped_column(Text)
    version: Mapped[str] = mapped_column(Text)
    granted_at: Mapped[datetime] = mapped_column(server_default=func.now())
    revoked_at: Mapped[datetime | None]
