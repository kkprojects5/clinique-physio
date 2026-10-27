"""Shapes for schedules (front desk) and a patient's own appointments."""

import uuid
from datetime import date, datetime

from pydantic import BaseModel


class TherapistRef(BaseModel):
    id: uuid.UUID
    first_name: str
    last_name: str


class PatientRef(BaseModel):
    """What the front desk needs to recognise and call a patient. No clinical data (B-CLN-05)."""

    id: uuid.UUID
    first_name: str
    last_name: str
    phone: str


class ServiceRef(BaseModel):
    id: uuid.UUID
    name_fr: str
    name_en: str
    duration_min: int


class DeskAppointment(BaseModel):
    id: uuid.UUID
    therapist_id: uuid.UUID
    start: datetime
    end: datetime
    start_local: str
    status: str
    service: ServiceRef
    patient: PatientRef


class DaySchedule(BaseModel):
    date: date
    therapists: list[TherapistRef]
    appointments: list[DeskAppointment]


class MyAppointment(BaseModel):
    id: uuid.UUID
    start: datetime
    end: datetime
    start_local: str
    status: str
    service: ServiceRef
    therapist: TherapistRef
