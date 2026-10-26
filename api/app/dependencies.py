"""Shared request dependencies: database session, the logged-in user, and role checks."""

import uuid
from typing import Annotated, Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import read_token_payload
from app.db.session import get_db
from app.models import User
from app.services.mfa_service import STAFF_ROLES
from app.services.session_service import ACCESS_PURPOSE

DbSession = Annotated[Session, Depends(get_db)]

_bearer = HTTPBearer(auto_error=False)

_NOT_AUTHENTICATED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated.",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_access_claims(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> dict[str, Any]:
    """Read 'Authorization: Bearer <access token>' and return its content, or answer 401."""
    if credentials is None:
        raise _NOT_AUTHENTICATED
    payload = read_token_payload(credentials.credentials, ACCESS_PURPOSE)
    if payload is None:
        raise _NOT_AUTHENTICATED
    return payload


AccessClaims = Annotated[dict[str, Any], Depends(get_access_claims)]


def get_current_user(db: DbSession, claims: AccessClaims) -> User:
    """The user the access token belongs to, or 401."""
    try:
        user = db.get(User, uuid.UUID(claims["sub"]))
    except (KeyError, ValueError):
        raise _NOT_AUTHENTICATED from None
    if user is None or not user.is_active:
        raise _NOT_AUTHENTICATED
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_staff(user: CurrentUser, claims: AccessClaims) -> User:
    """Staff endpoints: the role must be staff AND the token must carry mfa=true (B-AUTH-04).

    The role is read from the database, not from the token, so a role change applies at once.
    """
    if user.role not in STAFF_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Staff only.")
    if claims.get("mfa") is not True:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Two-factor authentication is required.",
        )
    return user


StaffUser = Annotated[User, Depends(require_staff)]
