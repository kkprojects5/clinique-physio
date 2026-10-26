"""Endpoints about the logged-in user."""

from fastapi import APIRouter

from app.dependencies import CurrentUser
from app.schemas.auth import MeResponse

router = APIRouter(prefix="/me", tags=["me"])


@router.get("")
def read_me(user: CurrentUser) -> MeResponse:
    """Who am I? Needs a valid access token."""
    return MeResponse(
        id=str(user.id),
        email=user.email,
        role=user.role,
        language=user.language,
        email_verified=user.email_verified_at is not None,
    )
