"""Endpoints about the logged-in user."""

from fastapi import APIRouter

from app.dependencies import CurrentPatient, CurrentUser, DbSession
from app.models import Service, Therapist
from app.schemas.auth import MeResponse
from app.schemas.billing import ReceiptRef
from app.schemas.schedule import MyAppointment, ServiceRef, TherapistRef
from app.services import billing_service, schedule_service
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


@router.get("/receipts")
def read_my_receipts(db: DbSession, patient: CurrentPatient) -> list[ReceiptRef]:
    """My past visits with a receipt for my insurer, newest first (B-BKG-10)."""
    found = []
    for appointment, billing in billing_service.my_receipts(db, patient):
        service = db.get(Service, appointment.service_id)
        therapist = db.get(Therapist, appointment.therapist_id)
        found.append(
            ReceiptRef(
                appointment_id=appointment.id,
                start=appointment.during.lower,
                service_fr=service.name_fr,
                service_en=service.name_en,
                therapist=f"{therapist.first_name} {therapist.last_name}",
                paid_cents=billing.paid_cents,
                receipt_number=billing_service.receipt_number(appointment),
            )
        )
    return found
