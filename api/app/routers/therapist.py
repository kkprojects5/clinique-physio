"""Therapist workspace (therapist + MFA only).

Own weekly hours and time off (B-AVL-02); patient files and SOAP notes with a care
relationship, every access audited (B-AUTH-05, B-CLN-01 to 05).
"""

import uuid

from fastapi import APIRouter, HTTPException, Request, status

from app.core.crypto import decrypt
from app.dependencies import CurrentTherapist, DbSession
from app.schemas.catalog import AvailabilityOut, ExceptionIn, ExceptionOut, RuleOut, RulesIn
from app.schemas.clinical import HistoryItem, MyPatient, NoteOut, PatientFile, SoapContent, SoapIn
from app.services import availability_service, clinical_service
from app.services.slots import CLINIC_TZ

router = APIRouter(prefix="/therapist", tags=["therapist"])


def _availability(db: DbSession, therapist) -> AvailabilityOut:
    rules, exceptions = availability_service.get_availability(db, therapist)
    return AvailabilityOut(
        rules=[
            RuleOut(weekday=r.weekday, start_time=r.start_time, end_time=r.end_time) for r in rules
        ],
        exceptions=[
            ExceptionOut(id=e.id, starts_at=e.during.lower, ends_at=e.during.upper, reason=e.reason)
            for e in exceptions
        ],
    )


@router.get("/availability")
def read_availability(db: DbSession, therapist: CurrentTherapist) -> AvailabilityOut:
    return _availability(db, therapist)


@router.put("/availability")
def replace_availability(
    data: RulesIn, db: DbSession, therapist: CurrentTherapist
) -> AvailabilityOut:
    """Replace the weekly schedule, e.g. Monday 08:00-16:00 (clinic local time)."""
    availability_service.replace_rules(
        db, therapist, [(r.weekday, r.start_time, r.end_time) for r in data.rules]
    )
    return _availability(db, therapist)


@router.post("/availability/exceptions", status_code=status.HTTP_201_CREATED)
def add_exception(data: ExceptionIn, db: DbSession, therapist: CurrentTherapist) -> ExceptionOut:
    """Time off: vacation, training, etc."""
    e = availability_service.add_exception(db, therapist, data.starts_at, data.ends_at, data.reason)
    return ExceptionOut(id=e.id, starts_at=e.during.lower, ends_at=e.during.upper, reason=e.reason)


@router.delete("/availability/exceptions/{exception_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_exception(exception_id: uuid.UUID, db: DbSession, therapist: CurrentTherapist) -> None:
    """Only your own time off. Someone else's id answers 404, revealing nothing."""
    if not availability_service.delete_exception(db, therapist, exception_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found.")


# --- Patient files and clinical notes ---------------------------------------------------


def _note_out(view: clinical_service.NoteView) -> NoteOut:
    n = view.note
    return NoteOut(
        id=n.id,
        appointment_id=n.appointment_id,
        patient_id=view.patient_id,
        author_therapist_id=n.therapist_id,
        content=SoapContent(**view.content),
        version=n.version,
        signed_at=n.signed_at,
        amends_note_id=n.amends_note_id,
        created_at=n.created_at,
        updated_at=n.updated_at,
    )


def _refused(error: clinical_service.ClinicalError) -> HTTPException:
    return HTTPException(status_code=error.status_code, detail=str(error))


def _content(data: SoapIn) -> dict[str, str]:
    if data.is_empty():
        raise HTTPException(status_code=422, detail="Fill in at least one part of the note.")
    return data.model_dump()


@router.get("/patients")
def list_my_patients(db: DbSession, therapist: CurrentTherapist) -> list[MyPatient]:
    """Patients I treat (care relationship), most recent visit first."""
    return [
        MyPatient(
            id=p.id,
            first_name=p.first_name,
            last_name=p.last_name,
            date_of_birth=p.date_of_birth,
            last_visit=visit,
        )
        for p, visit in clinical_service.my_patients(db, therapist)
    ]


@router.get("/patients/{patient_id}")
def read_patient_file(
    request: Request, patient_id: uuid.UUID, db: DbSession, therapist: CurrentTherapist
) -> PatientFile:
    """Profile and appointment history of a patient I treat. 404 otherwise. Audited."""
    try:
        patient, history = clinical_service.patient_file(db, therapist, patient_id, request)
    except clinical_service.ClinicalError as error:
        raise _refused(error) from None
    return PatientFile(
        id=patient.id,
        first_name=patient.first_name,
        last_name=patient.last_name,
        date_of_birth=patient.date_of_birth,
        phone=patient.phone,
        emergency_contact=decrypt(patient.emergency_contact_enc)
        if patient.emergency_contact_enc
        else None,
        history=[
            HistoryItem(
                appointment_id=a.id,
                start=a.during.lower,
                start_local=a.during.lower.astimezone(CLINIC_TZ).isoformat(),
                status=a.status,
                service_name_fr=s.name_fr,
                service_name_en=s.name_en,
                therapist_name=f"{t.first_name} {t.last_name}",
            )
            for a, s, t in history
        ],
    )


@router.get("/patients/{patient_id}/notes")
def list_patient_notes(
    request: Request, patient_id: uuid.UUID, db: DbSession, therapist: CurrentTherapist
) -> list[NoteOut]:
    """All notes of a patient I treat (with amendments). Each note read is audited."""
    try:
        views = clinical_service.patient_notes(db, therapist, patient_id, request)
    except clinical_service.ClinicalError as error:
        raise _refused(error) from None
    return [_note_out(v) for v in views]


@router.post("/appointments/{appointment_id}/notes", status_code=status.HTTP_201_CREATED)
def create_note(
    request: Request,
    appointment_id: uuid.UUID,
    data: SoapIn,
    db: DbSession,
    therapist: CurrentTherapist,
) -> NoteOut:
    """Write the draft note of one of my appointments, once it has taken place."""
    content = _content(data)
    try:
        view = clinical_service.create_note(db, therapist, appointment_id, content, request)
    except clinical_service.ClinicalError as error:
        raise _refused(error) from None
    return _note_out(view)


@router.get("/notes/{note_id}")
def read_note(
    request: Request, note_id: uuid.UUID, db: DbSession, therapist: CurrentTherapist
) -> NoteOut:
    """Read a note of a patient I treat. Audited."""
    try:
        view = clinical_service.read_note(db, therapist, note_id, request)
    except clinical_service.ClinicalError as error:
        raise _refused(error) from None
    return _note_out(view)


@router.put("/notes/{note_id}")
def update_note(
    request: Request,
    note_id: uuid.UUID,
    data: SoapIn,
    db: DbSession,
    therapist: CurrentTherapist,
) -> NoteOut:
    """Edit my draft note. A signed note answers 409."""
    content = _content(data)
    try:
        view = clinical_service.update_note(db, therapist, note_id, content, request)
    except clinical_service.ClinicalError as error:
        raise _refused(error) from None
    return _note_out(view)


@router.post("/notes/{note_id}/sign")
def sign_note(
    request: Request, note_id: uuid.UUID, db: DbSession, therapist: CurrentTherapist
) -> NoteOut:
    """Sign my draft: from now on it can never be changed."""
    try:
        view = clinical_service.sign_note(db, therapist, note_id, request)
    except clinical_service.ClinicalError as error:
        raise _refused(error) from None
    return _note_out(view)


@router.post("/notes/{note_id}/amendments", status_code=status.HTTP_201_CREATED)
def amend_note(
    request: Request,
    note_id: uuid.UUID,
    data: SoapIn,
    db: DbSession,
    therapist: CurrentTherapist,
) -> NoteOut:
    """Correct a signed note with a new signed note. The original stays as it was."""
    content = _content(data)
    try:
        view = clinical_service.amend_note(db, therapist, note_id, content, request)
    except clinical_service.ClinicalError as error:
        raise _refused(error) from None
    return _note_out(view)
