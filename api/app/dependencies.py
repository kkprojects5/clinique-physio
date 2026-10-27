"""Shared request dependencies: database session, the logged-in user, and role checks."""

import uuid
from typing import Annotated, Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import read_token_payload
from app.db.session import get_db
from app.models import Patient, Therapist, User
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


def require_therapist(db: DbSession, user: StaffUser) -> Therapist:
    """Therapist endpoints: a staff session (with MFA) whose role is therapist."""
    therapist = db.scalar(select(Therapist).where(Therapist.user_id == user.id))
    if user.role != "therapist" or therapist is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Therapists only.")
    return therapist


CurrentTherapist = Annotated[Therapist, Depends(require_therapist)]


def require_front_desk(user: StaffUser) -> User:
    """Front-desk endpoints: front desk or admin, with MFA. Therapists use their own workspace."""
    if user.role not in ("front_desk", "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Front desk only.")
    return user


FrontDeskUser = Annotated[User, Depends(require_front_desk)]


def require_patient(db: DbSession, user: CurrentUser) -> Patient:
    """Patient endpoints: the logged-in user's own patient record."""
    patient = db.scalar(select(Patient).where(Patient.user_id == user.id))
    if user.role != "patient" or patient is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Patients only.")
    return patient


CurrentPatient = Annotated[Patient, Depends(require_patient)]
