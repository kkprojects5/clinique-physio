"""Sending emails.

Development: the email is printed to the console so links can be tested.
A real provider is plugged in later (B-BKG-08). Recipients are masked in
logs: logs never contain personal information (NFR-13, B-C7).
"""

import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


def mask_email(email: str) -> str:
    """claire@example.com -> c***@example.com"""
    local, _, domain = email.partition("@")
    return f"{local[:1]}***@{domain}"


def send_email(to: str, subject: str, body: str) -> None:
    logger.info("email queued to=%s subject=%s", mask_email(to), subject)
    if settings.environment == "development":
        print(
            f"\n--- EMAIL (dev only) ---\nSubject: {subject}\n\n{body}\n------------------------\n"
        )
