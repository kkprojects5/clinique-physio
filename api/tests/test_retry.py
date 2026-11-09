"""Deadlock retry for write transactions (ADR-001)."""

import pytest
from psycopg.errors import DeadlockDetected
from sqlalchemy.exc import IntegrityError, OperationalError

from app.db import retry
from app.db.retry import MAX_ATTEMPTS, commit_with_retry, retry_on_deadlock


@pytest.fixture(autouse=True)
def waits(monkeypatch):
    """Record the waits instead of sleeping."""
    recorded = []
    monkeypatch.setattr(retry.time, "sleep", recorded.append)
    return recorded


class FakeSession:
    def __init__(self, log):
        self.log = log

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def commit(self):
        self.log.append("commit")

    def rollback(self):
        self.log.append("rollback")


def deadlock():
    return OperationalError("INSERT", {}, DeadlockDetected("deadlock detected"))


def test_a_deadlock_is_retried_in_a_fresh_session():
    log, attempts = [], []

    def work(session, attempt):
        attempts.append(attempt)
        if attempt == 1:
            raise deadlock()
        return "ok"

    assert commit_with_retry(lambda: FakeSession(log), work) == "ok"
    assert attempts == [1, 2]
    assert log == ["rollback", "commit"]


def test_gives_up_after_the_last_attempt():
    attempts = []

    def work(session, attempt):
        attempts.append(attempt)
        raise deadlock()

    with pytest.raises(OperationalError):
        commit_with_retry(lambda: FakeSession([]), work)
    assert attempts == list(range(1, MAX_ATTEMPTS + 1))


def test_each_retry_waits_a_random_time_that_grows(waits):
    def work(session, attempt):
        raise deadlock()

    with pytest.raises(OperationalError):
        commit_with_retry(lambda: FakeSession([]), work)

    assert len(waits) == MAX_ATTEMPTS - 1  # no wait after the last attempt
    for attempt, seconds in enumerate(waits, start=1):
        assert 0 < seconds <= retry.BASE_WAIT_MS * 2 ** (attempt - 1) / 1000


def test_request_session_retry_also_waits_and_succeeds(waits):
    log, calls = [], []

    class Db:
        def commit(self):
            log.append("commit")

        def rollback(self):
            log.append("rollback")

    def work():
        calls.append(1)
        if len(calls) < 3:
            raise deadlock()
        return "ok"

    assert retry_on_deadlock(Db(), work) == "ok"
    assert log == ["rollback", "rollback", "commit"]
    assert len(waits) == 2


def test_an_overlap_refusal_is_never_retried():
    attempts = []

    def work(session, attempt):
        attempts.append(attempt)
        raise IntegrityError("INSERT", {}, Exception("exclusion violation"))

    with pytest.raises(IntegrityError):
        commit_with_retry(lambda: FakeSession([]), work)
    assert attempts == [1]


def test_other_database_errors_are_not_retried():
    attempts = []

    def work(session, attempt):
        attempts.append(attempt)
        raise OperationalError("SELECT", {}, Exception("connection lost"))

    with pytest.raises(OperationalError):
        commit_with_retry(lambda: FakeSession([]), work)
    assert attempts == [1]
