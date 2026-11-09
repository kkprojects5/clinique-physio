"""Retry a write transaction when PostgreSQL cancels it because of a deadlock.

When many transactions insert overlapping appointments at the same moment, the exclusion
constraint (ADR-001) still never lets two of them win. But PostgreSQL sometimes resolves
the collision by cancelling a transaction with "deadlock detected" instead of reporting
the overlap. That is safe (nothing was saved), so the transaction is run again.

If all the cancelled transactions retried at once, they would collide again. So each retry
first waits a short random time that grows at each attempt (exponential backoff with jitter):
the retries spread out, and each one then either succeeds or gets the normal
"slot already taken" refusal.
"""

import secrets
import time
from collections.abc import Callable

from psycopg.errors import DeadlockDetected
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

MAX_ATTEMPTS = 6
BASE_WAIT_MS = 20  # waits up to 20, 40, 80, 160, 320 ms before retries 1 to 5


def is_deadlock(error: Exception) -> bool:
    return isinstance(error, OperationalError) and isinstance(error.orig, DeadlockDetected)


def backoff(attempt: int) -> None:
    """Wait a random time before retry number 'attempt' (1 = first retry)."""
    limit_ms = BASE_WAIT_MS * 2 ** (attempt - 1)
    time.sleep((1 + secrets.randbelow(limit_ms)) / 1000)


def commit_with_retry[T](
    make_session: Callable[[], Session],
    work: Callable[[Session, int], T],
    attempts: int = MAX_ATTEMPTS,
) -> T:
    """Run work(session, attempt) and commit, in a fresh session each time.

    Retries only on deadlock; any other error (including the overlap refusal) is raised.
    """
    for attempt in range(1, attempts + 1):
        with make_session() as session:
            try:
                result = work(session, attempt)
                session.commit()
                return result
            except OperationalError as error:
                session.rollback()
                if not is_deadlock(error) or attempt == attempts:
                    raise
        backoff(attempt)
    raise AssertionError("unreachable")  # pragma: no cover


def retry_on_deadlock[T](db: Session, work: Callable[[], T], attempts: int = MAX_ATTEMPTS) -> T:
    """Same as commit_with_retry, for the session of an API request: run work() and commit."""
    for attempt in range(1, attempts + 1):
        try:
            result = work()
            db.commit()
            return result
        except OperationalError as error:
            db.rollback()
            if not is_deadlock(error) or attempt == attempts:
                raise
        backoff(attempt)
    raise AssertionError("unreachable")  # pragma: no cover
