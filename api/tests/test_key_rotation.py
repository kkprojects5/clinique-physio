"""Rotation of the field encryption key (runbook: docs/runbook.md)."""

from datetime import UTC, datetime

import pytest
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from app.core import crypto
from app.core.config import settings
from app.models import AuditLog, ClinicalNote
from app.rotate_key import rotate_all
from tests.test_booking import at, clinic, place  # noqa: F401  (fixture)
from tests.test_schedules import make_patient

OLD = settings.field_encryption_key
NEW = Fernet.generate_key().decode()


@pytest.fixture
def new_key_first(monkeypatch):
    monkeypatch.setattr(settings, "field_encryption_key", f"{NEW},{OLD}")


def signed_note(db, clinic):  # noqa: F811
    marie = make_patient(db, "Marie")
    marie.emergency_contact_enc = crypto.encrypt("Paul, 514-555-0102")
    appointment = place(db, marie, clinic["anne"], clinic["treatment"], at(9), status="completed")
    note = ClinicalNote(
        appointment_id=appointment.id,
        therapist_id=clinic["anne"].id,
        content_encrypted=crypto.encrypt('{"subjective": "Douleur au genou"}'),
        signed_at=datetime.now(UTC),
    )
    db.add(note)
    db.commit()
    return marie, note


def test_several_keys_read_old_values_and_write_with_the_first(new_key_first):
    old_value = Fernet(OLD.encode()).encrypt(b"secret")

    assert crypto.decrypt(old_value) == "secret"
    assert Fernet(NEW.encode()).decrypt(crypto.encrypt("secret")) == b"secret"


def test_rotation_re_encrypts_everything_with_the_new_key(db, clinic, new_key_first):  # noqa: F811
    marie, note = signed_note(db, clinic)

    counts = rotate_all(db)
    db.commit()

    assert counts["clinical_notes.content_encrypted"] >= 1
    assert counts["patients.emergency_contact_enc"] >= 1
    only_new = Fernet(NEW.encode())
    db.refresh(note)
    db.refresh(marie)
    assert only_new.decrypt(note.content_encrypted) == b'{"subjective": "Douleur au genou"}'
    assert only_new.decrypt(marie.emergency_contact_enc) == b"Paul, 514-555-0102"
    with pytest.raises(InvalidToken):
        Fernet(OLD.encode()).decrypt(note.content_encrypted)  # the old key is no longer needed
    assert db.scalar(select(AuditLog).where(AuditLog.action == "key_rotation")) is not None


def test_a_signed_note_stays_locked_outside_a_rotation(db, clinic):  # noqa: F811
    _, note = signed_note(db, clinic)

    with pytest.raises(DBAPIError, match="cannot be changed"), db.begin_nested():
        note.content_encrypted = crypto.encrypt("changed")
        db.flush()


def test_a_rotation_cannot_change_anything_else_on_a_signed_note(db, clinic):  # noqa: F811
    _, note = signed_note(db, clinic)

    with pytest.raises(DBAPIError, match="cannot be changed"), db.begin_nested():
        db.execute(text("SET LOCAL app.key_rotation = 'on'"))
        note.version = 2
        db.flush()


def test_running_it_twice_does_no_harm(db, clinic, new_key_first):  # noqa: F811
    _, note = signed_note(db, clinic)
    rotate_all(db)

    rotate_all(db)

    assert crypto.decrypt(note.content_encrypted) == '{"subjective": "Douleur au genou"}'
