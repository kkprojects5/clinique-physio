"""Password hashing and signed tokens.

Passwords are hashed with Argon2id (NFR-02, B-AUTH-03): a slow, memory-hard
algorithm, so a stolen database cannot be brute-forced quickly.
"""

from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError

from app.core.config import settings

_hasher = PasswordHasher()  # argon2-cffi uses Argon2id by default
_ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except VerificationError:
        return False


def create_token(subject: str, purpose: str, lifetime: timedelta) -> str:
    """Create a signed token. 'purpose' stops a token made for one use being used for another."""
    now = datetime.now(UTC)
    payload = {"sub": subject, "purpose": purpose, "iat": now, "exp": now + lifetime}
    return jwt.encode(payload, settings.jwt_secret, algorithm=_ALGORITHM)


def read_token(token: str, purpose: str) -> str | None:
    """Return the token's subject, or None if it is invalid, expired or for another purpose."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[_ALGORITHM])
    except jwt.PyJWTError:
        return None
    if payload.get("purpose") != purpose:
        return None
    return payload.get("sub")
