"""Authentication endpoints. Thin layer: validation by the schemas, logic in the services."""

from typing import Annotated

from fastapi import APIRouter, Cookie, HTTPException, Response, status
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.dependencies import DbSession
from app.schemas.auth import (
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    TokenResponse,
    VerifyEmailRequest,
)
from app.services import auth_service, session_service

router = APIRouter(prefix="/auth", tags=["auth"])

REGISTER_MESSAGE = "If this email address can be used, a confirmation link has been sent to it."

# The refresh token lives in an httpOnly cookie: JavaScript cannot read it,
# so an XSS attack cannot steal it (challenge B-C4). It is only sent to /api/v1/auth.
REFRESH_COOKIE = "refresh_token"
REFRESH_COOKIE_PATH = "/api/v1/auth"

RefreshCookie = Annotated[str | None, Cookie(alias=REFRESH_COOKIE)]


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        REFRESH_COOKIE,
        token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path=REFRESH_COOKIE_PATH,
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        REFRESH_COOKIE,
        path=REFRESH_COOKIE_PATH,
        secure=settings.cookie_secure,
        httponly=True,
        samesite=settings.cookie_samesite,
    )


def _token_response(access_token: str) -> TokenResponse:
    return TokenResponse(access_token=access_token, expires_in=settings.access_token_minutes * 60)


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


@router.post("/login")
def login(data: LoginRequest, response: Response, db: DbSession) -> TokenResponse:
    """Log in. Wrong email and wrong password get the same answer."""
    try:
        user = session_service.authenticate(db, data.email, data.password)
    except session_service.InvalidCredentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password."
        ) from None
    except session_service.EmailNotVerified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please confirm your email address before logging in.",
        ) from None

    access_token, refresh_token = session_service.start_session(db, user)
    _set_refresh_cookie(response, refresh_token)
    return _token_response(access_token)


@router.post("/refresh", response_model=TokenResponse)
def refresh(response: Response, db: DbSession, refresh_token: RefreshCookie = None):
    """Get a new access token using the refresh cookie. The cookie is replaced too."""
    try:
        _, access_token, new_refresh = session_service.refresh_session(db, refresh_token)
    except session_service.InvalidSession:
        error = JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Session expired. Please log in again."},
        )
        _clear_refresh_cookie(error)
        return error
    _set_refresh_cookie(response, new_refresh)
    return _token_response(access_token)


@router.post("/logout")
def logout(
    response: Response, db: DbSession, refresh_token: RefreshCookie = None
) -> MessageResponse:
    """End the session: the refresh token stops working and the cookie is removed."""
    session_service.end_session(db, refresh_token)
    _clear_refresh_cookie(response)
    return MessageResponse(message="Logged out.")
