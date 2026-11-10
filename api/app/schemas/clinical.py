"""Schemas for patient files and SOAP notes (therapists only)."""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field

NOTE_FIELD = Field(default="", max_length=5000)


class SoapIn(BaseModel):
    """SOAP note: Subjective, Objective, Assessment, Plan. At least one part must be filled."""

    subjective: str = NOTE_FIELD
    objective: str = NOTE_FIELD
    assessment: str = NOTE_FIELD
    plan: str = NOTE_FIELD

    def is_empty(self) -> bool:
        return not any(v.strip() for v in self.model_dump().values())


class SoapContent(BaseModel):
    subjective: str
    objective: str
    assessment: str
    plan: str


class NoteOut(BaseModel):
    id: uuid.UUID
    appointment_id: uuid.UUID
    patient_id: uuid.UUID
    author_therapist_id: uuid.UUID
    content: SoapContent
    version: int
    signed_at: datetime | None
    amends_note_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class MyPatient(BaseModel):
    id: uuid.UUID
    first_name: str
    last_name: str
    date_of_birth: date
    last_visit: datetime | None


class HistoryItem(BaseModel):
    appointment_id: uuid.UUID
    start: datetime
    start_local: str
    status: str
    service_name_fr: str
    service_name_en: str
    therapist_id: uuid.UUID
    therapist_name: str


class PatientFile(BaseModel):
    id: uuid.UUID
    first_name: str
    last_name: str
    date_of_birth: date
    phone: str
    emergency_contact: str | None
    history: list[HistoryItem]
