"""Deadlock retry for write transactions (ADR-001)."""

import pytest
from psycopg.errors import DeadlockDetected
from sqlalchemy.exc import IntegrityError, OperationalError

from app.db.retry import commit_with_retry


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


def test_gives_up_after_three_deadlocks():
    def work(session, attempt):
        raise deadlock()

    with pytest.raises(OperationalError):
        commit_with_retry(lambda: FakeSession([]), work)


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
