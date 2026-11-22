"""Weekly reports for the administrator (B-ADM-02).

One week, Monday to Sunday in Montréal time:
- appointments: every booking of the week that was not an expired or unpaid hold;
- seen: the patient came (checked in or completed); no-shows; cancellations by who cancelled;
- no-show rate = no-shows / (seen + no-shows): of the patients expected, how many did not come;
- occupancy = booked minutes / working minutes. Booked minutes count confirmed, seen and
  no-show appointments (the time was reserved). Working minutes are the therapists' weekly
  hours minus their time off;
- revenue = money received during the week (deposits + desk payments - refunds), by payment
  date, so it matches the bank statement.

Only counts and totals: no patient names, so the report holds no personal information.
"""

import uuid
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import Range
from sqlalchemy.orm import Session

from app.models import (
    Appointment,
    AvailabilityException,
    AvailabilityRule,
    Payment,
    Therapist,
    User,
)
from app.services.slots import local_to_utc

COUNTED = (
    "confirmed",
    "checked_in",
    "completed",
    "cancelled_by_patient",
    "cancelled_by_clinic",
    "no_show",
)
SEEN = ("checked_in", "completed")
BOOKED = ("confirmed", "checked_in", "completed", "no_show")


@dataclass
class TherapistWeek:
    therapist: Therapist
    appointments: int = 0
    seen: int = 0
    no_shows: int = 0
    booked_minutes: int = 0
    working_minutes: int = 0

    @property
    def occupancy(self) -> float | None:
        return (
            round(self.booked_minutes / self.working_minutes, 3) if self.working_minutes else None
        )


@dataclass
class WeekReport:
    week_start: date
    statuses: Counter = field(default_factory=Counter)
    revenue_cents: int = 0
    deposits_cents: int = 0
    desk_cents: int = 0
    refunds_cents: int = 0
    therapists: list[TherapistWeek] = field(default_factory=list)

    @property
    def week_end(self) -> date:
        return self.week_start + timedelta(days=6)

    @property
    def appointments(self) -> int:
        return sum(self.statuses.values())

    @property
    def seen(self) -> int:
        return sum(self.statuses[s] for s in SEEN)

    @property
    def no_shows(self) -> int:
        return self.statuses["no_show"]

    @property
    def no_show_rate(self) -> float | None:
        expected = self.seen + self.no_shows
        return round(self.no_shows / expected, 3) if expected else None

    @property
    def occupancy(self) -> float | None:
        working = sum(t.working_minutes for t in self.therapists)
        booked = sum(t.booked_minutes for t in self.therapists)
        return round(booked / working, 3) if working else None


def monday_of(day: date) -> date:
    return day - timedelta(days=day.weekday())


def _minutes(start: datetime, end: datetime) -> int:
    return max(int((end - start).total_seconds() // 60), 0)


def _working_minutes(db: Session, therapist_id: uuid.UUID, monday: date) -> int:
    """Weekly hours of that week, minus the time off that falls inside them."""
    rules = db.scalars(
        select(AvailabilityRule).where(AvailabilityRule.therapist_id == therapist_id)
    )
    windows = []
    for rule in rules:
        day = monday + timedelta(days=rule.weekday - 1)
        windows.append((local_to_utc(day, rule.start_time), local_to_utc(day, rule.end_time)))
    week = Range(local_to_utc(monday, time()), local_to_utc(monday + timedelta(days=7), time()))
    off = db.scalars(
        select(AvailabilityException).where(
            AvailabilityException.therapist_id == therapist_id,
            AvailabilityException.during.overlaps(week),
        )
    ).all()
    total = 0
    for start, end in windows:
        total += _minutes(start, end)
        for exception in off:
            total -= _minutes(max(start, exception.during.lower), min(end, exception.during.upper))
    return max(total, 0)


def weekly(db: Session, any_day: date) -> WeekReport:
    monday = monday_of(any_day)
    report = WeekReport(week_start=monday)
    start = local_to_utc(monday, time())
    end = local_to_utc(monday + timedelta(days=7), time())

    therapists = db.scalars(
        select(Therapist)
        .join(User, User.id == Therapist.user_id)
        .where(User.is_active.is_(True))
        .order_by(Therapist.last_name, Therapist.first_name)
    ).all()
    rows = {
        t.id: TherapistWeek(t, working_minutes=_working_minutes(db, t.id, monday))
        for t in therapists
    }

    appointments = db.scalars(
        select(Appointment).where(
            # counted in the week it starts
            func.lower(Appointment.during) >= start,
            func.lower(Appointment.during) < end,
            Appointment.status.in_(COUNTED),
        )
    ).all()
    for a in appointments:
        report.statuses[a.status] += 1
        row = rows.get(a.therapist_id)
        if row is None:  # a therapist deactivated since then still counts in the totals
            row = rows[a.therapist_id] = TherapistWeek(db.get(Therapist, a.therapist_id))
        row.appointments += 1
        row.seen += a.status in SEEN
        row.no_shows += a.status == "no_show"
        if a.status in BOOKED:
            row.booked_minutes += _minutes(a.during.lower, a.during.upper)

    payments = db.scalars(
        select(Payment).where(
            Payment.status == "succeeded", Payment.created_at >= start, Payment.created_at < end
        )
    ).all()
    for p in payments:
        if p.type == "deposit":
            report.deposits_cents += p.amount_cents
        elif p.type == "balance":
            report.desk_cents += p.amount_cents
        else:
            report.refunds_cents += p.amount_cents
    report.revenue_cents = report.deposits_cents + report.desk_cents - report.refunds_cents
    report.therapists = list(rows.values())
    return report
