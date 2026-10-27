"""Front-desk endpoints (desktop app). Front desk or admin, with MFA."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query

from app.dependencies import DbSession, FrontDeskUser
from app.schemas.schedule import DaySchedule, DeskAppointment, PatientRef, ServiceRef, TherapistRef
from app.services import schedule_service
from app.services.slots import CLINIC_TZ

router = APIRouter(prefix="/desk", tags=["front desk"])


@router.get("/schedule")
def read_day_schedule(
    day: Annotated[date, Query(alias="date")], db: DbSession, _: FrontDeskUser
) -> DaySchedule:
    """Every therapist's appointments for one day (?date=2026-11-02, Montréal time)."""
    therapists, rows = schedule_service.day_schedule(db, day)
    return DaySchedule(
        date=day,
        therapists=[
            TherapistRef(id=t.id, first_name=t.first_name, last_name=t.last_name)
            for t in therapists
        ],
        appointments=[
            DeskAppointment(
                id=a.id,
                therapist_id=a.therapist_id,
                start=a.during.lower,
                end=a.during.upper,
                start_local=a.during.lower.astimezone(CLINIC_TZ).isoformat(),
                status=a.status,
                service=ServiceRef(
                    id=s.id, name_fr=s.name_fr, name_en=s.name_en, duration_min=s.duration_min
                ),
                patient=PatientRef(
                    id=p.id, first_name=p.first_name, last_name=p.last_name, phone=p.phone
                ),
            )
            for a, p, s in rows
        ],
    )
