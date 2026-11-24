"""Field-level encryption for sensitive data stored in the database.

Fernet = AES-128 in CBC mode with an HMAC signature. The key lives in an
environment variable, never in the database, so a database leak alone does
not reveal the encrypted fields.

Key rotation (runbook, docs/runbook.md): FIELD_ENCRYPTION_KEY can hold several keys separated
by commas, the new one first ("new,old"). New values are encrypted with the first key; values
encrypted with any listed key can still be read. `python -m app.rotate_key` then re-encrypts
every stored value with the first key, after which the old key can be removed.
"""

from functools import lru_cache

from cryptography.fernet import Fernet, MultiFernet

from app.core.config import settings


def keys(value: str | None = None) -> list[str]:
    """The keys in FIELD_ENCRYPTION_KEY, the one used for new values first."""
    raw = settings.field_encryption_key if value is None else value
    return [k.strip() for k in raw.split(",") if k.strip()]


@lru_cache(maxsize=4)
def _cipher(raw: str) -> MultiFernet:
    return MultiFernet([Fernet(k.encode()) for k in keys(raw)])


def _current() -> MultiFernet:
    return _cipher(settings.field_encryption_key)


def encrypt(value: str) -> bytes:
    return _current().encrypt(value.encode())


def decrypt(value: bytes) -> str:
    return _current().decrypt(value).decode()


def rotate(value: bytes) -> bytes:
    """The same value, encrypted again with the first key (any listed key can read it)."""
    return _current().rotate(value)
