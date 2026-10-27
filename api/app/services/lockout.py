"""Account lockout after repeated failures (B-AUTH-06).

After 5 failed attempts in a row (wrong password or wrong MFA code), the account
is locked for 15 minutes. While locked, every attempt gets the usual generic
"incorrect email or password" answer, so the lockout reveals nothing to an attacker.
The account owner is told by email.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import User
from app.services.email import send_email

LOCK_SUBJECT = {
    "fr": "Votre compte est temporairement verrouillé",
    "en": "Your account is temporarily locked",
}
LOCK_BODY = {
    "fr": "Trop de tentatives de connexion ont échoué. Réessayez dans {minutes} minutes. "
    "Si ce n'était pas vous, changez votre mot de passe.",
    "en": "Too many failed login attempts. Try again in {minutes} minutes. "
    "If this was not you, change your password.",
}


def is_locked(user: User) -> bool:
    return user.locked_until is not None and user.locked_until > datetime.now(UTC)


def register_failure(db: Session, user: User) -> None:
    """Count one failure; lock the account when the limit is reached."""
    user.failed_login_count += 1
    if user.failed_login_count >= settings.max_failed_logins:
        user.locked_until = datetime.now(UTC) + timedelta(minutes=settings.lockout_minutes)
        user.failed_login_count = 0
        send_email(
            user.email,
            LOCK_SUBJECT[user.language],
            LOCK_BODY[user.language].format(minutes=settings.lockout_minutes),
        )
    db.commit()


def register_success(user: User) -> None:
    user.failed_login_count = 0
    user.locked_until = None
