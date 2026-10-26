"""Shared request dependencies: database session and the logged-in user."""

import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import read_token_payload
from app.db.session import get_db
from app.models import User
from app.services.session_service import ACCESS_PURPOSE

DbSession = Annotated[Session, Depends(get_db)]

_bearer = HTTPBearer(auto_error=False)

_NOT_AUTHENTICATED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated.",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    """Read 'Authorization: Bearer <access token>' and return the user, or answer 401."""
    if credentials is None:
        raise _NOT_AUTHENTICATED
    payload = read_token_payload(credentials.credentials, ACCESS_PURPOSE)
    if payload is None:
        raise _NOT_AUTHENTICATED
    try:
        user = db.get(User, uuid.UUID(payload["sub"]))
    except (KeyError, ValueError):
        raise _NOT_AUTHENTICATED from None
    if user is None or not user.is_active:
        raise _NOT_AUTHENTICATED
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
