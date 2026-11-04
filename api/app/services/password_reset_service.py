"""Password reset by email link (B-AUTH-03).

- Asking for a reset gets the same answer whether or not the email has an account,
  and the email is sent in the background, so the answer time reveals nothing either.
- The link holds a long random token. Only its SHA-256 hash is stored, like refresh tokens.
- A link works once, for 30 minutes. Asking again cancels the previous link.
- After a reset every session is cancelled (someone else may have been logged in),
  the account is unlocked, and the owner is told by email.
- Staff still need their 6-digit code after a reset: a reset never bypasses MFA.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password, hash_refresh_token, new_refresh_token
from app.models import PasswordResetToken, RefreshToken, User
from app.services.email import send_email

RESET_SUBJECT = {"fr": "Réinitialisez votre mot de passe", "en": "Reset your password"}
RESET_BODY = {
    "fr": "Pour choisir un nouveau mot de passe, ouvrez ce lien (valide {minutes} minutes, "
    "une seule fois) : {link}\n\nSi vous n'avez rien demandé, ignorez ce courriel.",
    "en": "To choose a new password, open this link (valid {minutes} minutes, once only): "
    "{link}\n\nIf you did not ask for this, ignore this email.",
}
CHANGED_SUBJECT = {"fr": "Votre mot de passe a été modifié", "en": "Your password was changed"}
CHANGED_BODY = {
    "fr": "Le mot de passe de votre compte vient d'être modifié et toutes vos sessions ont été "
    "fermées. Si ce n'était pas vous, contactez la clinique immédiatement.",
    "en": "Your account password was just changed and all your sessions were closed. "
    "If this was not you, contact the clinic immediately.",
}


class InvalidResetToken(Exception):
    """Unknown, expired or already used link. Never says which."""


class WeakPassword(Exception):
    """The new password contains the email address."""


@dataclass
class Email:
    to: str
    subject: str
    body: str

    def send(self) -> None:
        send_email(self.to, self.subject, self.body)


def request_reset(db: Session, email: str) -> Email | None:
    """Create a reset link. Returns the email to send, or None if there is no such account.

    The caller answers the same way in both cases and sends the email in the background.
    """
    user = db.scalar(select(User).where(User.email == email.lower()))
    if user is None or not user.is_active:
        return None

    now = datetime.now(UTC)
    # Only the newest link works: older unused links are cancelled.
    db.execute(
        update(PasswordResetToken)
        .where(PasswordResetToken.user_id == user.id, PasswordResetToken.used_at.is_(None))
        .values(used_at=now)
    )
    raw = new_refresh_token()  # same kind of long random value
    db.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=hash_refresh_token(raw),
            expires_at=now + timedelta(minutes=settings.password_reset_minutes),
        )
    )
    db.commit()

    link = f"{settings.web_base_url}/reinitialiser-mot-de-passe?token={raw}"
    body = RESET_BODY[user.language].format(minutes=settings.password_reset_minutes, link=link)
    return Email(user.email, RESET_SUBJECT[user.language], body)


def reset_password(db: Session, raw_token: str, new_password: str) -> Email:
    """Set the new password. Returns the 'password changed' email to send."""
    now = datetime.now(UTC)
    # FOR UPDATE: if the same link is used twice at the same moment, only one succeeds.
    stored = db.scalar(
        select(PasswordResetToken)
        .where(PasswordResetToken.token_hash == hash_refresh_token(raw_token))
        .with_for_update()
    )
    if stored is None or stored.used_at is not None or stored.expires_at <= now:
        raise InvalidResetToken
    user = db.get(User, stored.user_id)
    if user is None or not user.is_active:
        raise InvalidResetToken

    # Same rule as at registration. Checked before the link is used up, so it can be retried.
    if user.email.split("@")[0].lower() in new_password.lower():
        raise WeakPassword

    stored.used_at = now
    user.password_hash = hash_password(new_password)
    user.failed_login_count = 0
    user.locked_until = None
    if user.email_verified_at is None:
        user.email_verified_at = now  # the link proves they control this mailbox
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=now)
    )
    db.commit()
    return Email(user.email, CHANGED_SUBJECT[user.language], CHANGED_BODY[user.language])
