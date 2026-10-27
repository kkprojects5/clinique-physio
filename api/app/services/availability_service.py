"""Services catalog, therapist availability and slot search (B-AVL-01 to 03).

Database work only; the slot arithmetic itself is in app/services/slots.py.
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import and_, delete, or_, select
from sqlalchemy.dialects.postgresql import Range
from sqlalchemy.orm import Session

from app.models import (
    ACTIVE_STATUSES,
    Appointment,
    AvailabilityException,
    AvailabilityRule,
    Service,
    Therapist,
    TherapistService,
)
from app.services.slots import CLINIC_TZ, Period, WeeklyRule, compute_slots, local_to_utc

MAX_RANGE_DAYS = 31  # one search covers at most a month (no unbounded results, NFR-07)
MAX_DAYS_AHEAD = 60  # patients cannot book more than 60 days ahead (BR-B-05)


class InvalidSearch(Exception):
    """The slot search parameters are not acceptable; the message says why."""


@dataclass
class Slot:
    therapist_id: uuid.UUID
    period: Period


def _links(db: Session) -> list[TherapistService]:
    return list(db.scalars(select(TherapistService)))


def list_services(db: Session) -> list[tuple[Service, list[uuid.UUID]]]:
    services = db.scalars(
        select(Service).where(Service.is_active.is_(True)).order_by(Service.name_fr)
    ).all()
    links = _links(db)
    return [(s, [link.therapist_id for link in links if link.service_id == s.id]) for s in services]


def list_therapists(db: Session) -> list[tuple[Therapist, list[uuid.UUID]]]:
    therapists = db.scalars(select(Therapist).order_by(Therapist.last_name)).all()
    links = _links(db)
    return [
        (t, [link.service_id for link in links if link.therapist_id == t.id]) for t in therapists
    ]


def today_local() -> date:
    return datetime.now(CLINIC_TZ).date()


def find_slots(
    db: Session,
    service_id: uuid.UUID,
    therapist_id: uuid.UUID | None,
    date_from: date,
    date_to: date,
) -> list[Slot]:
    """Free slots for a service, for one therapist or all therapists who provide it."""
    today = today_local()
    if date_to < date_from:
        raise InvalidSearch("date_to must be on or after date_from")
    if (date_to - date_from).days >= MAX_RANGE_DAYS:
        raise InvalidSearch(f"search at most {MAX_RANGE_DAYS} days at a time")
    date_from = max(date_from, today)  # nothing in the past
    date_to = min(date_to, today + timedelta(days=MAX_DAYS_AHEAD))
    if date_to < date_from:
        return []

    service = db.get(Service, service_id)
    if service is None or not service.is_active:
        raise InvalidSearch("unknown service")

    query = select(TherapistService.therapist_id).where(TherapistService.service_id == service_id)
    if therapist_id is not None:
        query = query.where(TherapistService.therapist_id == therapist_id)
    therapist_ids = list(db.scalars(query))

    range_start = local_to_utc(date_from, datetime.min.time())
    range_end = local_to_utc(date_to + timedelta(days=1), datetime.min.time())
    search = Range(range_start, range_end)
    now = datetime.now(UTC)

    slots: list[Slot] = []
    for tid in therapist_ids:
        rules = [
            WeeklyRule(r.weekday, r.start_time, r.end_time)
            for r in db.scalars(
                select(AvailabilityRule).where(AvailabilityRule.therapist_id == tid)
            )
        ]
        exceptions = [
            Period(e.during.lower, e.during.upper)
            for e in db.scalars(
                select(AvailabilityException).where(
                    AvailabilityException.therapist_id == tid,
                    AvailabilityException.during.overlaps(search),
                )
            )
        ]
        appointments = [
            Period(a.during.lower, a.during.upper)
            for a in db.scalars(
                select(Appointment).where(
                    Appointment.therapist_id == tid,
                    Appointment.during.overlaps(search),
                    Appointment.status.in_(ACTIVE_STATUSES),
                    # an expired 10-minute hold no longer blocks the slot (B-BKG-03)
                    or_(
                        Appointment.status != "held",
                        Appointment.hold_expires_at.is_(None),
                        Appointment.hold_expires_at > now,
                    ),
                )
            )
        ]
        for period in compute_slots(
            rules=rules,
            exceptions=exceptions,
            appointments=appointments,
            duration_minutes=service.duration_min,
            first_day=date_from,
            last_day=date_to,
            not_before=now,
        ):
            slots.append(Slot(tid, period))

    return sorted(slots, key=lambda s: (s.period.start, str(s.therapist_id)))


# --- Therapist's own availability (B-AVL-02) --------------------------------


def get_availability(
    db: Session, therapist: Therapist
) -> tuple[list[AvailabilityRule], list[AvailabilityException]]:
    rules = db.scalars(
        select(AvailabilityRule)
        .where(AvailabilityRule.therapist_id == therapist.id)
        .order_by(AvailabilityRule.weekday, AvailabilityRule.start_time)
    ).all()
    exceptions = db.scalars(
        select(AvailabilityException)
        .where(AvailabilityException.therapist_id == therapist.id)
        .order_by(AvailabilityException.during)
    ).all()
    return list(rules), list(exceptions)


def replace_rules(db: Session, therapist: Therapist, rules: list[tuple[int, time, time]]) -> None:
    """Replace the whole weekly schedule in one transaction."""
    db.execute(delete(AvailabilityRule).where(AvailabilityRule.therapist_id == therapist.id))
    for weekday, start, end in rules:
        db.add(
            AvailabilityRule(
                therapist_id=therapist.id, weekday=weekday, start_time=start, end_time=end
            )
        )
    db.commit()


def add_exception(
    db: Session, therapist: Therapist, starts_at: datetime, ends_at: datetime, reason: str | None
) -> AvailabilityException:
    exception = AvailabilityException(
        therapist_id=therapist.id, during=Range(starts_at, ends_at), reason=reason
    )
    db.add(exception)
    db.commit()
    return exception


def delete_exception(db: Session, therapist: Therapist, exception_id: uuid.UUID) -> bool:
    """Delete only if it belongs to this therapist (ownership check, B-C3)."""
    result = db.execute(
        delete(AvailabilityException).where(
            and_(
                AvailabilityException.id == exception_id,
                AvailabilityException.therapist_id == therapist.id,
            )
        )
    )
    db.commit()
    return result.rowcount == 1
