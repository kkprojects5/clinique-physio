"""Password hashing and signed tokens.

Passwords are hashed with Argon2id (NFR-02, B-AUTH-03): a slow, memory-hard
algorithm, so a stolen database cannot be brute-forced quickly.
"""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError

from app.core.config import settings

_hasher = PasswordHasher()  # argon2-cffi uses Argon2id by default
_ALGORITHM = "HS256"

# Used when the email does not exist, so a failed login always takes the same time.
DUMMY_HASH = _hasher.hash("not-a-real-password-used-for-timing-only")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except VerificationError:
        return False


def create_token(
    subject: str, purpose: str, lifetime: timedelta, extra: dict[str, Any] | None = None
) -> str:
    """Create a signed token. 'purpose' stops a token made for one use being used for another."""
    now = datetime.now(UTC)
    payload = {"sub": subject, "purpose": purpose, "iat": now, "exp": now + lifetime}
    payload.update(extra or {})
    return jwt.encode(payload, settings.jwt_secret, algorithm=_ALGORITHM)


def read_token_payload(token: str, purpose: str) -> dict[str, Any] | None:
    """Return the token's content, or None if it is invalid, expired or for another purpose."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[_ALGORITHM])
    except jwt.PyJWTError:
        return None
    if payload.get("purpose") != purpose:
        return None
    return payload


def read_token(token: str, purpose: str) -> str | None:
    """Return only the token's subject (the user id), or None."""
    payload = read_token_payload(token, purpose)
    return payload.get("sub") if payload else None


def new_refresh_token() -> str:
    """A long random value. The client keeps it; the database keeps only its hash."""
    return secrets.token_urlsafe(32)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
