"""Two-factor authentication with TOTP codes for staff (B-AUTH-04).

TOTP = time-based one-time password: the authenticator app and the server share a
secret and both compute a 6-digit code that changes every 30 seconds (RFC 6238).
The secret is stored encrypted, and each code can be used only once.
"""

import hmac
import uuid
from datetime import UTC, datetime, timedelta

import pyotp
from sqlalchemy.orm import Session

from app.core.crypto import decrypt, encrypt
from app.core.security import create_token, read_token
from app.models import User
from app.services import lockout

STAFF_ROLES = ("therapist", "front_desk", "admin")
MFA_PENDING_PURPOSE = "mfa_pending"
MFA_PENDING_MINUTES = 5
ISSUER = "Clinique Physio Mont-Royal"


class InvalidMfaTicket(Exception):
    """The 'MFA pending' ticket is missing, expired or invalid."""


class InvalidCode(Exception):
    """Wrong, expired or already used code."""


class AlreadyEnrolled(Exception):
    """MFA is already set up; it cannot be set up again with only a password."""


def is_staff(user: User) -> bool:
    return user.role in STAFF_ROLES


def create_mfa_ticket(user: User) -> str:
    """Proof that the password was correct. Valid 5 minutes, only for the MFA step."""
    return create_token(str(user.id), MFA_PENDING_PURPOSE, timedelta(minutes=MFA_PENDING_MINUTES))


def user_from_ticket(db: Session, ticket: str) -> User:
    subject = read_token(ticket, MFA_PENDING_PURPOSE)
    if subject is None:
        raise InvalidMfaTicket
    try:
        user = db.get(User, uuid.UUID(subject))
    except ValueError:
        raise InvalidMfaTicket from None
    if user is None or not user.is_active or not is_staff(user) or lockout.is_locked(user):
        raise InvalidMfaTicket
    return user


def start_enrolment(db: Session, user: User) -> tuple[str, str]:
    """Create a new secret. Returns (secret, otpauth URI to show as a QR code)."""
    if user.mfa_enabled_at is not None:
        raise AlreadyEnrolled
    secret = pyotp.random_base32()
    user.mfa_secret_enc = encrypt(secret)
    db.commit()
    uri = pyotp.TOTP(secret).provisioning_uri(name=user.email, issuer_name=ISSUER)
    return secret, uri


def verify_code(db: Session, user: User, code: str) -> None:
    """Accept the current code (or the one just before/after, for clock drift), once only."""
    if user.mfa_secret_enc is None:
        raise InvalidCode
    totp = pyotp.TOTP(decrypt(user.mfa_secret_enc))
    current_step = totp.timecode(datetime.now(UTC))

    for step in (current_step - 1, current_step, current_step + 1):
        if hmac.compare_digest(totp.generate_otp(step), code):
            if user.mfa_last_used_step is not None and step <= user.mfa_last_used_step:
                raise InvalidCode  # replay of a code already used
            user.mfa_last_used_step = step
            if user.mfa_enabled_at is None:
                user.mfa_enabled_at = datetime.now(UTC)  # first code confirms enrolment
            lockout.register_success(user)
            db.commit()
            return
    lockout.register_failure(db, user)  # wrong codes count toward the lockout too
    raise InvalidCode
