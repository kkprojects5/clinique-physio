"""Rate limiting per client IP address (NFR-05), using slowapi.

Above the limit the API answers 429 Too Many Requests. In production behind a
proxy (Render), uvicorn must run with --proxy-headers so the real client IP is used.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings

limiter = Limiter(key_func=get_remote_address, enabled=settings.rate_limit_enabled)

LOGIN_LIMIT = "5/minute"
MFA_LIMIT = "5/minute"
REGISTER_LIMIT = "5/minute"
VERIFY_EMAIL_LIMIT = "10/minute"
REFRESH_LIMIT = "30/minute"
