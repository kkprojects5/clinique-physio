"""Patient files and SOAP notes for therapists (B-AUTH-05, B-CLN-01 to 05).

- A therapist sees a patient only with a care relationship: at least one real appointment
  together (confirmed, checked in or completed). Otherwise the patient "does not exist" (404),
  and the refused attempt is audited.
- Notes are written by the therapist of the appointment, once the appointment has started.
- The note content (Subjective, Objective, Assessment, Plan) is encrypted by the API with a key
  kept outside the database. Front desk and admin never reach these functions (role check).
- Drafts can be edited by their author. Signed notes are locked (also by a database trigger);
  a correction is a signed amendment pointing to the original (B-CLN-03).
- Every read, write, signature and refusal is written to the audit log in the same transaction.
"""

import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from fastapi import Request
from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session

from app.core.crypto import decrypt, encrypt
from app.models import Appointment, ClinicalNote, Patient, Service, Therapist
from app.services import audit_service

CARE_STATUSES = ("confirmed", "checked_in", "completed")
SOAP_FIELDS = ("subjective", "objective", "assessment", "plan")


class ClinicalError(Exception):
    status_code = 409


class NotFound(ClinicalError):
    status_code = 404

    def __init__(self) -> None:
        super().__init__("Not found.")


@dataclass
class NoteView:
    note: ClinicalNote
    patient_id: uuid.UUID
    content: dict[str, str]


def has_care_relationship(db: Session, therapist: Therapist, patient_id: uuid.UUID) -> bool:
    return bool(
        db.scalar(
            select(
                exists().where(
                    Appointment.therapist_id == therapist.id,
                    Appointment.patient_id == patient_id,
                    Appointment.status.in_(CARE_STATUSES),
                )
            )
        )
    )


def _deny(db, therapist, resource_type, resource_id, patient_id, request) -> NotFound:
    """Audit the refused attempt, commit it, and return the 404 to raise."""
    db.rollback()
    audit_service.log(
        db, therapist.user_id, "access_denied", resource_type, resource_id, patient_id, request
    )
    db.commit()
    return NotFound()


def my_patients(db: Session, therapist: Therapist) -> list[tuple[Patient, datetime | None]]:
    """Patients I treat, with their last appointment start (most recent first)."""
    last = func.max(func.lower(Appointment.during)).label("last_visit")
    rows = db.execute(
        select(Patient, last)
        .join(Appointment, Appointment.patient_id == Patient.id)
        .where(Appointment.therapist_id == therapist.id, Appointment.status.in_(CARE_STATUSES))
        .group_by(Patient.id)
        .order_by(last.desc())
    ).all()
    return [(patient, visit) for patient, visit in rows]


def patient_file(
    db: Session, therapist: Therapist, patient_id: uuid.UUID, request: Request | None = None
) -> tuple[Patient, list[tuple[Appointment, Service, Therapist]]]:
    """A patient's profile and appointment history, if I treat them. Audited."""
    patient = db.get(Patient, patient_id)
    if patient is None or not has_care_relationship(db, therapist, patient_id):
        raise _deny(db, therapist, "patient", patient_id, patient and patient.id, request)
    history = db.execute(
        select(Appointment, Service, Therapist)
        .join(Service, Service.id == Appointment.service_id)
        .join(Therapist, Therapist.id == Appointment.therapist_id)
        .where(Appointment.patient_id == patient_id, Appointment.status != "expired")
        .order_by(func.lower(Appointment.during).desc())
        .limit(100)
    ).all()
    audit_service.log(db, therapist.user_id, "read", "patient", patient_id, patient_id, request)
    db.commit()
    return patient, [tuple(row) for row in history]


def _encrypt(content: dict[str, str]) -> bytes:
    return encrypt(json.dumps({k: content.get(k, "") for k in SOAP_FIELDS}, ensure_ascii=False))


def _decrypt(note: ClinicalNote) -> dict[str, str]:
    return json.loads(decrypt(note.content_encrypted))


def _patient_of(db: Session, note: ClinicalNote) -> uuid.UUID:
    return db.scalar(select(Appointment.patient_id).where(Appointment.id == note.appointment_id))


def create_note(
    db: Session,
    therapist: Therapist,
    appointment_id: uuid.UUID,
    content: dict[str, str],
    request: Request | None = None,
) -> NoteView:
    """Draft note for one of my appointments that has started. One original note per appointment."""
    appointment = db.get(Appointment, appointment_id)
    if appointment is None or appointment.therapist_id != therapist.id:
        raise _deny(
            db,
            therapist,
            "appointment",
            appointment_id,
            appointment.patient_id if appointment else None,
            request,
        )
    if appointment.status not in CARE_STATUSES or appointment.during.lower > datetime.now(UTC):
        raise ClinicalError("A note can be written once the appointment has taken place.")
    already = db.scalar(
        select(
            exists().where(
                ClinicalNote.appointment_id == appointment.id, ClinicalNote.amends_note_id.is_(None)
            )
        )
    )
    if already:
        raise ClinicalError("This appointment already has a note. Edit it, or add an amendment.")
    note = ClinicalNote(
        id=uuid.uuid4(),
        appointment_id=appointment.id,
        therapist_id=therapist.id,
        content_encrypted=_encrypt(content),
    )
    db.add(note)
    db.flush()
    audit_service.log(
        db, therapist.user_id, "create", "clinical_note", note.id, appointment.patient_id, request
    )
    db.commit()
    return NoteView(note, appointment.patient_id, _decrypt(note))


def _readable(
    db: Session, therapist: Therapist, note_id: uuid.UUID, request: Request | None
) -> tuple[ClinicalNote, uuid.UUID]:
    note = db.get(ClinicalNote, note_id)
    patient_id = _patient_of(db, note) if note else None
    if note is None or not has_care_relationship(db, therapist, patient_id):
        raise _deny(db, therapist, "clinical_note", note_id, patient_id, request)
    return note, patient_id


def read_note(
    db: Session, therapist: Therapist, note_id: uuid.UUID, request: Request | None = None
) -> NoteView:
    """Any therapist who treats the patient can read the note. Every read is audited."""
    note, patient_id = _readable(db, therapist, note_id, request)
    audit_service.log(db, therapist.user_id, "read", "clinical_note", note.id, patient_id, request)
    db.commit()
    return NoteView(note, patient_id, _decrypt(note))


def patient_notes(
    db: Session, therapist: Therapist, patient_id: uuid.UUID, request: Request | None = None
) -> list[NoteView]:
    """All notes of a patient I treat, oldest first. Each note returned is audited as read."""
    if not has_care_relationship(db, therapist, patient_id):
        raise _deny(db, therapist, "patient", patient_id, patient_id, request)
    notes = db.scalars(
        select(ClinicalNote)
        .join(Appointment, Appointment.id == ClinicalNote.appointment_id)
        .where(Appointment.patient_id == patient_id)
        .order_by(ClinicalNote.created_at)
    ).all()
    for note in notes:
        audit_service.log(
            db, therapist.user_id, "read", "clinical_note", note.id, patient_id, request
        )
    db.commit()
    return [NoteView(note, patient_id, _decrypt(note)) for note in notes]


def _own_draft(db, therapist, note_id, request) -> tuple[ClinicalNote, uuid.UUID]:
    note, patient_id = _readable(db, therapist, note_id, request)
    if note.therapist_id != therapist.id:
        raise ClinicalError("Only the author can change a note.")
    if note.signed_at is not None:
        raise ClinicalError("This note is signed and can no longer be changed. Add an amendment.")
    return note, patient_id


def update_note(
    db: Session,
    therapist: Therapist,
    note_id: uuid.UUID,
    content: dict[str, str],
    request: Request | None = None,
) -> NoteView:
    note, patient_id = _own_draft(db, therapist, note_id, request)
    note.content_encrypted = _encrypt(content)
    note.version += 1
    note.updated_at = datetime.now(UTC)
    audit_service.log(
        db, therapist.user_id, "update", "clinical_note", note.id, patient_id, request
    )
    db.commit()
    return NoteView(note, patient_id, _decrypt(note))


def sign_note(
    db: Session, therapist: Therapist, note_id: uuid.UUID, request: Request | None = None
) -> NoteView:
    note, patient_id = _own_draft(db, therapist, note_id, request)
    note.signed_at = datetime.now(UTC)
    audit_service.log(db, therapist.user_id, "sign", "clinical_note", note.id, patient_id, request)
    db.commit()
    return NoteView(note, patient_id, _decrypt(note))


def amend_note(
    db: Session,
    therapist: Therapist,
    note_id: uuid.UUID,
    content: dict[str, str],
    request: Request | None = None,
) -> NoteView:
    """Correct a signed note: a new signed note pointing to it. The original is kept."""
    original, patient_id = _readable(db, therapist, note_id, request)
    if original.signed_at is None:
        raise ClinicalError("A draft is edited directly; only signed notes take amendments.")
    amendment = ClinicalNote(
        id=uuid.uuid4(),
        appointment_id=original.appointment_id,
        therapist_id=therapist.id,
        content_encrypted=_encrypt(content),
        amends_note_id=original.id,
        signed_at=datetime.now(UTC),
    )
    db.add(amendment)
    db.flush()
    audit_service.log(
        db, therapist.user_id, "amend", "clinical_note", amendment.id, patient_id, request
    )
    db.commit()
    return NoteView(amendment, patient_id, _decrypt(amendment))
