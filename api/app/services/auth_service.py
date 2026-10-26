"""Business rules for registration and email verification.

Routers stay thin: all logic lives here (NFR-11).
"""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.crypto import encrypt
from app.core.security import create_token, hash_password, read_token
from app.models import Consent, Patient, User
from app.schemas.auth import RegisterRequest
from app.services.email import send_email

EMAIL_VERIFY_PURPOSE = "email_verify"

VERIFY_SUBJECT = {"fr": "Confirmez votre adresse courriel", "en": "Confirm your email address"}
VERIFY_BODY = {
    "fr": "Bienvenue à la Clinique Physio Mont-Royal. Confirmez votre adresse : {link}",
    "en": "Welcome to Clinique Physio Mont-Royal. Confirm your address: {link}",
}


def register_patient(db: Session, data: RegisterRequest) -> None:
    """Create a patient account, or do nothing visible if the email is already used.

    The caller always gets the same answer, so nobody can find out whether an
    email address has an account (no user enumeration, B-AUTH-03).
    """
    email = data.email.lower()
    password_hash = hash_password(data.password)  # always hash: same timing in both cases

    if db.scalar(select(User.id).where(User.email == email)) is not None:
        return

    user = User(email=email, password_hash=password_hash, role="patient", language=data.language)
    db.add(user)
    db.flush()  # gives user.id

    db.add(
        Patient(
            user_id=user.id,
            first_name=data.first_name.strip(),
            last_name=data.last_name.strip(),
            date_of_birth=data.date_of_birth,
            phone=data.phone.strip(),
            emergency_contact_enc=(
                encrypt(data.emergency_contact) if data.emergency_contact else None
            ),
        )
    )
    db.add(Consent(user_id=user.id, type="privacy_policy", version=settings.privacy_policy_version))
    if data.accept_electronic_comms:
        db.add(
            Consent(
                user_id=user.id, type="electronic_comms", version=settings.privacy_policy_version
            )
        )
    db.commit()

    token = create_token(
        str(user.id), EMAIL_VERIFY_PURPOSE, timedelta(hours=settings.email_verification_hours)
    )
    link = f"{settings.web_base_url}/verify-email?token={token}"
    send_email(email, VERIFY_SUBJECT[data.language], VERIFY_BODY[data.language].format(link=link))


def verify_email(db: Session, token: str) -> bool:
    """Mark the email as verified. Returns False if the token is invalid or expired."""
    subject = read_token(token, EMAIL_VERIFY_PURPOSE)
    if subject is None:
        return False
    try:
        user_id = uuid.UUID(subject)
    except ValueError:
        return False

    user = db.get(User, user_id)
    if user is None:
        return False
    if user.email_verified_at is None:
        user.email_verified_at = datetime.now(UTC)
        db.commit()
    return True
