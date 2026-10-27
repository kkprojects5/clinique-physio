"""Therapist workspace: own weekly hours and time off (B-AVL-02). Therapist + MFA only."""

import uuid

from fastapi import APIRouter, HTTPException, status

from app.dependencies import CurrentTherapist, DbSession
from app.schemas.catalog import AvailabilityOut, ExceptionIn, ExceptionOut, RuleOut, RulesIn
from app.services import availability_service

router = APIRouter(prefix="/therapist", tags=["therapist"])


def _availability(db: DbSession, therapist) -> AvailabilityOut:
    rules, exceptions = availability_service.get_availability(db, therapist)
    return AvailabilityOut(
        rules=[
            RuleOut(weekday=r.weekday, start_time=r.start_time, end_time=r.end_time) for r in rules
        ],
        exceptions=[
            ExceptionOut(id=e.id, starts_at=e.during.lower, ends_at=e.during.upper, reason=e.reason)
            for e in exceptions
        ],
    )


@router.get("/availability")
def read_availability(db: DbSession, therapist: CurrentTherapist) -> AvailabilityOut:
    return _availability(db, therapist)


@router.put("/availability")
def replace_availability(
    data: RulesIn, db: DbSession, therapist: CurrentTherapist
) -> AvailabilityOut:
    """Replace the weekly schedule, e.g. Monday 08:00-16:00 (clinic local time)."""
    availability_service.replace_rules(
        db, therapist, [(r.weekday, r.start_time, r.end_time) for r in data.rules]
    )
    return _availability(db, therapist)


@router.post("/availability/exceptions", status_code=status.HTTP_201_CREATED)
def add_exception(data: ExceptionIn, db: DbSession, therapist: CurrentTherapist) -> ExceptionOut:
    """Time off: vacation, training, etc."""
    e = availability_service.add_exception(db, therapist, data.starts_at, data.ends_at, data.reason)
    return ExceptionOut(id=e.id, starts_at=e.during.lower, ends_at=e.during.upper, reason=e.reason)


@router.delete("/availability/exceptions/{exception_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_exception(exception_id: uuid.UUID, db: DbSession, therapist: CurrentTherapist) -> None:
    """Only your own time off. Someone else's id answers 404, revealing nothing."""
    if not availability_service.delete_exception(db, therapist, exception_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found.")
