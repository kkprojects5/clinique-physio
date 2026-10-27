"""Reading schedules: the whole clinic's day (front desk) and a patient's own appointments."""

from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import or_, select
from sqlalchemy.dialects.postgresql import Range
from sqlalchemy.orm import Session

from app.models import Appointment, Patient, Service, Therapist
from app.services.slots import local_to_utc

MY_APPOINTMENTS_LIMIT = 50  # lists are never unbounded (NFR-07)


def _not_expired_hold(now: datetime):
    """A 'held' appointment whose 10-minute hold has passed is no longer real."""
    return or_(
        Appointment.status != "held",
        Appointment.hold_expires_at.is_(None),
        Appointment.hold_expires_at > now,
    )


def day_schedule(db: Session, day: date):
    """All appointments of one clinic day (Montréal time), for every therapist."""
    start = local_to_utc(day, time(0))
    end = local_to_utc(day + timedelta(days=1), time(0))  # 23 or 25 hours on DST days
    rows = db.execute(
        select(Appointment, Patient, Service)
        .join(Patient, Patient.id == Appointment.patient_id)
        .join(Service, Service.id == Appointment.service_id)
        .where(
            Appointment.during.overlaps(Range(start, end)),
            _not_expired_hold(datetime.now(UTC)),
        )
        .order_by(Appointment.during)
    ).all()
    therapists = db.scalars(select(Therapist).order_by(Therapist.last_name)).all()
    return therapists, rows


def my_upcoming(db: Session, patient: Patient):
    """The patient's own appointments that have not ended yet, soonest first."""
    now = datetime.now(UTC)
    return db.execute(
        select(Appointment, Service, Therapist)
        .join(Service, Service.id == Appointment.service_id)
        .join(Therapist, Therapist.id == Appointment.therapist_id)
        .where(
            Appointment.patient_id == patient.id,  # ownership: only this patient's rows (B-C3)
            Appointment.during.overlaps(Range(now, None)),
            _not_expired_hold(now),
        )
        .order_by(Appointment.during)
        .limit(MY_APPOINTMENTS_LIMIT)
    ).all()
