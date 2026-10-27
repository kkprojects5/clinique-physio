"""Endpoints about the logged-in user."""

from fastapi import APIRouter

from app.dependencies import CurrentPatient, CurrentUser, DbSession
from app.schemas.auth import MeResponse
from app.schemas.schedule import MyAppointment, ServiceRef, TherapistRef
from app.services import schedule_service
from app.services.slots import CLINIC_TZ

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


@router.get("/appointments")
def read_my_appointments(db: DbSession, patient: CurrentPatient) -> list[MyAppointment]:
    """My upcoming appointments (patients only, and only their own)."""
    return [
        MyAppointment(
            id=a.id,
            start=a.during.lower,
            end=a.during.upper,
            start_local=a.during.lower.astimezone(CLINIC_TZ).isoformat(),
            status=a.status,
            service=ServiceRef(
                id=s.id, name_fr=s.name_fr, name_en=s.name_en, duration_min=s.duration_min
            ),
            therapist=TherapistRef(id=t.id, first_name=t.first_name, last_name=t.last_name),
        )
        for a, s, t in schedule_service.my_upcoming(db, patient)
    ]
