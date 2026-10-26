"""Authentication endpoints. Thin layer: validation by the schemas, logic in the service."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.auth import MessageResponse, RegisterRequest, VerifyEmailRequest
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])

DbSession = Annotated[Session, Depends(get_db)]

REGISTER_MESSAGE = "If this email address can be used, a confirmation link has been sent to it."


@router.post("/register", status_code=status.HTTP_202_ACCEPTED)
def register(data: RegisterRequest, db: DbSession) -> MessageResponse:
    """Create a patient account. Same answer whether or not the email already exists."""
    auth_service.register_patient(db, data)
    return MessageResponse(message=REGISTER_MESSAGE)


@router.post("/verify-email")
def verify_email(data: VerifyEmailRequest, db: DbSession) -> MessageResponse:
    """Confirm the email address with the token sent by email."""
    if not auth_service.verify_email(db, data.token):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This confirmation link is invalid or has expired.",
        )
    return MessageResponse(message="Email address confirmed.")
