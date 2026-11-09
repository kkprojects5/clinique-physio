"""Audit log of access to patient files (B-CLN-04).

Each entry says who did what, on which patient, when, from which IP and which app.
The entry is written in the same transaction as the action, so an action is never saved
without its trace. The table itself refuses changes and deletions (database trigger).
"""

import uuid

from fastapi import Request
from sqlalchemy.orm import Session

from app.models import AuditLog

CLIENT_APPS = {"web", "mobile", "desktop"}


def client_info(request: Request | None) -> tuple[str | None, str | None]:
    """IP (the real client behind Render's proxy) and the app named in X-Client-App."""
    if request is None:
        return None, None
    ip = request.client.host if request.client else None
    app = request.headers.get("x-client-app", "").lower()
    return ip, app if app in CLIENT_APPS else "other"


def log(
    db: Session,
    actor_id: uuid.UUID | None,
    action: str,
    resource_type: str,
    resource_id: uuid.UUID | None = None,
    patient_id: uuid.UUID | None = None,
    request: Request | None = None,
) -> None:
    """Add an entry. The caller commits it with the action itself."""
    ip, app = client_info(request)
    db.add(
        AuditLog(
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            patient_id=patient_id,
            ip=ip if ip and ip != "testclient" else None,
            client_app=app,
        )
    )
