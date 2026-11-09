"""Schemas for the exercise library and home programs."""

import uuid
from datetime import date

from pydantic import BaseModel, Field

from app.schemas.schedule import TherapistRef


class ExerciseOut(BaseModel):
    id: uuid.UUID
    name_fr: str
    name_en: str
    description_fr: str
    description_en: str
    instructions_fr: str
    instructions_en: str
    image_url: str | None
    default_sets: int
    default_reps: int


class ProgramItemIn(BaseModel):
    exercise_id: uuid.UUID
    sets: int | None = Field(default=None, ge=1, le=10)  # empty: the exercise's default
    reps: int | None = Field(default=None, ge=1, le=100)
    times_per_week: int = Field(ge=1, le=14)


class ProgramIn(BaseModel):
    start_date: date
    weeks: int = Field(ge=1, le=26)
    notes: str | None = Field(default=None, max_length=2000)
    items: list[ProgramItemIn] = Field(min_length=1, max_length=20)


class ProgramItemOut(BaseModel):
    id: uuid.UUID
    exercise: ExerciseOut
    sets: int
    reps: int
    times_per_week: int
    done_total: int
    planned_total: int
    done_this_week: int
    done_today: bool


class ProgramOut(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    therapist: TherapistRef
    start_date: date
    end_date: date  # first day after the program
    weeks: int
    notes: str | None
    adherence_percent: int  # sessions done / sessions planned, all exercises
    items: list[ProgramItemOut]


class CheckOffIn(BaseModel):
    pain_level: int | None = Field(default=None, ge=0, le=10)


class CheckOffOut(BaseModel):
    id: uuid.UUID
    program_item_id: uuid.UUID
    done_on: date
    pain_level: int | None
