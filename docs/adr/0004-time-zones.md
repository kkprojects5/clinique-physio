# ADR-0004: Store times in UTC, define schedules in clinic local time

- Status: Accepted (D1)
- Requirements: B-BKG-07, B-AVL-03, challenge B-C2

## Context

The clinic is in Montréal (`America/Toronto` time zone), which changes between UTC-4 and UTC-5
twice a year. An appointment booked for 10:00 on the Monday after the November change must still
show 10:00. The 24-hour cancellation rule must be exact across the change. Patients and staff may
use devices set to other time zones.

## Decision

1. **Every moment is stored in UTC** (`timestamptz`, and `tstzrange` for appointments).
2. **Working hours are stored in clinic local time** (`time` columns, e.g. Monday 08:00 to 16:00),
   because that is what they mean on both sides of a change.
3. Slots are computed **day by day**: each day's local hours are converted to UTC with the rules of
   *that* date, then candidates are stepped every 15 minutes of real time (so a 23-hour or 25-hour
   day is handled).
4. The API returns times in UTC **and** in clinic local time with its offset
   (`start_local: "2026-11-02T10:00:00-05:00"`); clients display clinic time, never the device's.

## Alternatives considered

| Alternative | Why not |
|---|---|
| Store local times without a time zone | Ambiguous during the repeated hour in November; impossible to compare correctly across the change. |
| Store working hours in UTC | "Monday 08:00" would become 07:00 or 09:00 after a change. |
| Convert on the device | Devices may be set to another time zone; results would differ between clients. |

## Consequences

- Proven by `api/tests/test_slots.py` (November 2026 and March 2027 changes, 25- and 23-hour
  nights), the web tests (`web/src/utils/format.test.js`), the desktop tests and the mobile tests.
- Every client shows the same time for the same appointment.
