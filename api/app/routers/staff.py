"""Endpoints for staff (therapists, front desk, admin). All require MFA."""

from fastapi import APIRouter

from app.dependencies import StaffUser
from app.schemas.auth import StaffSessionResponse

router = APIRouter(prefix="/staff", tags=["staff"])


@router.get("/session")
def staff_session(user: StaffUser) -> StaffSessionResponse:
    """Used by the desktop and web staff screens to check the session is a valid staff session."""
    return StaffSessionResponse(email=user.email, role=user.role, mfa=True)
