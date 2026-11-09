"""Make bookings for the same therapist take turns (ADR-001).

Under heavy contention, inserts checked by an exclusion constraint can keep forming wait
cycles (deadlocks) with each other. Taking a transaction lock per therapist just before the
insert puts competing bookings in a queue instead: the next one waits, then sees the slot
taken and gets the normal "slot already taken" refusal. The lock is released automatically
at the end of the transaction. Bookings for different therapists do not wait for each other.

The exclusion constraint remains the guarantee; this lock only makes conflicts orderly.
"""

import uuid

from sqlalchemy import text
from sqlalchemy.orm import Session


def lock_therapist_schedule(session: Session, therapist_id: uuid.UUID) -> None:
    session.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
        {"key": f"therapist-schedule:{therapist_id}"},
    )
