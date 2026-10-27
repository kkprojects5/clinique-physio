"""Bookable slot computation (B-AVL-03).

    available slots = therapist working hours
                      - time off (exceptions)
                      - existing active appointments (with a 5-minute buffer)

- Working hours are in clinic local time (America/Toronto). Each day's window is
  converted to UTC with the time zone rules of THAT date, so daylight saving
  changes are handled: "Monday 10:00" is 10:00 local before and after the change.
- Slot starts are on a 15-minute grid of local time (:00, :15, :30, :45).
- Candidates are stepped in real (UTC) time, so a day with 23 or 25 hours is correct.

This module has no database code: it takes plain data and is tested on its own.
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

CLINIC_TZ = ZoneInfo("America/Toronto")
GRID_MINUTES = 15
BUFFER_MINUTES = 5


@dataclass(frozen=True)
class WeeklyRule:
    weekday: int  # 1 = Monday ... 7 = Sunday (ISO)
    start: time  # local clock time
    end: time


@dataclass(frozen=True)
class Period:
    """A time interval in UTC: [start, end)."""

    start: datetime
    end: datetime

    def overlaps(self, other: "Period") -> bool:
        return self.start < other.end and other.start < self.end


def local_to_utc(day: date, clock: time) -> datetime:
    return datetime.combine(day, clock, tzinfo=CLINIC_TZ).astimezone(UTC)


def _first_grid_start(window_start_utc: datetime) -> datetime:
    """Round up to the next :00/:15/:30/:45 of local time."""
    local = window_start_utc.astimezone(CLINIC_TZ)
    extra = local.minute % GRID_MINUTES
    rounded = local.replace(second=0, microsecond=0)
    if extra or local.second or local.microsecond:
        rounded += timedelta(minutes=GRID_MINUTES - extra)
    return rounded.astimezone(UTC)


def compute_slots(
    *,
    rules: list[WeeklyRule],
    exceptions: list[Period],
    appointments: list[Period],
    duration_minutes: int,
    first_day: date,
    last_day: date,
    not_before: datetime,
) -> list[Period]:
    """Return the free slots of one therapist between first_day and last_day (local dates)."""
    duration = timedelta(minutes=duration_minutes)
    buffer = timedelta(minutes=BUFFER_MINUTES)
    step = timedelta(minutes=GRID_MINUTES)
    # An appointment blocks its own time plus 5 minutes before and after.
    blocked = [Period(a.start - buffer, a.end + buffer) for a in appointments] + exceptions

    slots: list[Period] = []
    day = first_day
    while day <= last_day:
        for rule in rules:
            if rule.weekday != day.isoweekday():
                continue
            window_start = local_to_utc(day, rule.start)
            window_end = local_to_utc(day, rule.end)
            start = _first_grid_start(window_start)
            while start + duration <= window_end:
                slot = Period(start, start + duration)
                if start >= not_before and not any(slot.overlaps(b) for b in blocked):
                    slots.append(slot)
                start += step
        day += timedelta(days=1)

    return sorted(slots, key=lambda s: s.start)
