"""Field-level encryption for sensitive data stored in the database.

Fernet = AES-128 in CBC mode with an HMAC signature. The key lives in an
environment variable, never in the database, so a database leak alone does
not reveal the encrypted fields.
"""

from cryptography.fernet import Fernet

from app.core.config import settings

_fernet = Fernet(settings.field_encryption_key.encode())


def encrypt(value: str) -> bytes:
    return _fernet.encrypt(value.encode())


def decrypt(value: bytes) -> str:
    return _fernet.decrypt(value).decode()
