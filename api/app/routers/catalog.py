"""Public booking information: services, therapists and free slots (B-AVL-01, 03)."""

import uuid
from datetime import date

from fastapi import APIRouter, HTTPException, status

from app.dependencies import DbSession
from app.schemas.catalog import ServiceOut, SlotOut, TherapistOut
from app.services import availability_service
from app.services.slots import CLINIC_TZ

router = APIRouter(tags=["catalog"])


@router.get("/services")
def list_services(db: DbSession) -> list[ServiceOut]:
    """Active services with price, deposit and the therapists who provide them."""
    return [
        ServiceOut(
            id=s.id,
            name_fr=s.name_fr,
            name_en=s.name_en,
            description_fr=s.description_fr,
            description_en=s.description_en,
            duration_min=s.duration_min,
            price_cents=s.price_cents,
            deposit_cents=s.deposit_cents,
            is_initial_evaluation=s.is_initial_evaluation,
            therapist_ids=therapist_ids,
        )
        for s, therapist_ids in availability_service.list_services(db)
    ]


@router.get("/therapists")
def list_therapists(db: DbSession) -> list[TherapistOut]:
    """The team. No licence number or account details: public information only."""
    return [
        TherapistOut(
            id=t.id,
            first_name=t.first_name,
            last_name=t.last_name,
            specialties=t.specialties,
            languages=t.languages,
            bio_fr=t.bio_fr,
            bio_en=t.bio_en,
            service_ids=service_ids,
        )
        for t, service_ids in availability_service.list_therapists(db)
    ]


@router.get("/availability")
def list_slots(
    db: DbSession,
    service_id: uuid.UUID,
    date_from: date,
    date_to: date,
    therapist_id: uuid.UUID | None = None,
) -> list[SlotOut]:
    """Free slots for a service. Without therapist_id: "first available" across the team."""
    try:
        slots = availability_service.find_slots(db, service_id, therapist_id, date_from, date_to)
    except availability_service.InvalidSearch as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from None
    return [
        SlotOut(
            therapist_id=slot.therapist_id,
            start=slot.period.start,
            end=slot.period.end,
            start_local=slot.period.start.astimezone(CLINIC_TZ).isoformat(),
        )
        for slot in slots
    ]
