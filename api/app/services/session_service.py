"""Login sessions: login, refresh token rotation and logout (B-AUTH-02).

- The access token is short-lived (10 min) and signed; the API does not store it.
- The refresh token is a random value sent in an httpOnly cookie. The database
  keeps only its hash. Each refresh replaces it with a new one (rotation).
- If an old, already-replaced refresh token is used again, it was probably
  stolen: every session of that user is cancelled.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    DUMMY_HASH,
    create_token,
    hash_refresh_token,
    new_refresh_token,
    verify_password,
)
from app.models import RefreshToken, User
from app.services import lockout

ACCESS_PURPOSE = "access"


class InvalidCredentials(Exception):
    """Wrong email or password. Never says which one."""


class EmailNotVerified(Exception):
    """Correct password, but the email address is not confirmed yet."""


class InvalidSession(Exception):
    """Missing, expired, revoked or unknown refresh token."""


def authenticate(db: Session, email: str, password: str) -> User:
    user = db.scalar(select(User).where(User.email == email.lower()))
    if user is None:
        verify_password(DUMMY_HASH, password)  # same work, so timing reveals nothing
        raise InvalidCredentials
    if lockout.is_locked(user):
        verify_password(DUMMY_HASH, password)  # same answer and timing as a wrong password
        raise InvalidCredentials
    if not verify_password(user.password_hash, password):
        lockout.register_failure(db, user)
        raise InvalidCredentials
    if not user.is_active:
        raise InvalidCredentials
    if user.email_verified_at is None:
        raise EmailNotVerified
    lockout.register_success(user)
    user.last_login_at = datetime.now(UTC)
    return user


def refresh_lifetime(user: User) -> timedelta:
    """Staff: 15 minutes, renewed at each refresh, so inactivity logs them out."""
    if user.role == "patient":
        return timedelta(days=settings.refresh_token_days_patient)
    return timedelta(minutes=settings.staff_inactivity_minutes)


def access_token_for(user: User, mfa: bool) -> str:
    """'mfa' says whether the user passed the two-factor check (required for staff)."""
    return create_token(
        str(user.id),
        ACCESS_PURPOSE,
        timedelta(minutes=settings.access_token_minutes),
        extra={"role": user.role, "mfa": mfa},
    )


def _issue_refresh_token(db: Session, user: User) -> str:
    raw = new_refresh_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(raw),
            expires_at=datetime.now(UTC) + refresh_lifetime(user),
        )
    )
    return raw


def start_session(db: Session, user: User, mfa: bool = False) -> tuple[str, str]:
    """Return (access token, refresh token) for a user who just logged in."""
    refresh = _issue_refresh_token(db, user)
    db.commit()
    return access_token_for(user, mfa), refresh


def refresh_session(db: Session, raw_refresh: str | None) -> tuple[User, str, str]:
    """Swap a valid refresh token for a new pair. The old one stops working."""
    if not raw_refresh:
        raise InvalidSession
    stored = db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(raw_refresh))
    )
    if stored is None:
        raise InvalidSession

    now = datetime.now(UTC)
    if stored.revoked_at is not None:
        # Reuse of a replaced token: assume theft and cancel every session of this user.
        db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == stored.user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        db.commit()
        raise InvalidSession
    if stored.expires_at <= now:
        raise InvalidSession

    user = db.get(User, stored.user_id)
    if user is None or not user.is_active:
        raise InvalidSession

    stored.revoked_at = now
    new_refresh = _issue_refresh_token(db, user)
    db.commit()
    # Staff only receive a refresh token after passing MFA, so their session keeps mfa=True.
    return user, access_token_for(user, mfa=user.role != "patient"), new_refresh


def end_session(db: Session, raw_refresh: str | None) -> None:
    """Logout: the refresh token can no longer be used."""
    if not raw_refresh:
        return
    stored = db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(raw_refresh))
    )
    if stored is not None and stored.revoked_at is None:
        stored.revoked_at = datetime.now(UTC)
        db.commit()
