"""Exercise library, home programs and check-offs (B-EXE-01 to 04)."""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    SmallInteger,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Exercise(Base):
    """One exercise of the clinic's library, in French and English."""

    __tablename__ = "exercises"
    __table_args__ = (
        CheckConstraint("default_sets BETWEEN 1 AND 10", name="ck_exercises_sets"),
        CheckConstraint("default_reps BETWEEN 1 AND 100", name="ck_exercises_reps"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    name_fr: Mapped[str] = mapped_column(Text)
    name_en: Mapped[str] = mapped_column(Text)
    description_fr: Mapped[str] = mapped_column(Text)
    description_en: Mapped[str] = mapped_column(Text)
    instructions_fr: Mapped[str] = mapped_column(Text)
    instructions_en: Mapped[str] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(Text)
    default_sets: Mapped[int] = mapped_column(SmallInteger)
    default_reps: Mapped[int] = mapped_column(SmallInteger)
    is_active: Mapped[bool] = mapped_column(server_default=text("true"))


class Program(Base):
    """A home exercise program given by a therapist to a patient, for a number of weeks."""

    __tablename__ = "programs"
    __table_args__ = (CheckConstraint("weeks BETWEEN 1 AND 26", name="ck_programs_weeks"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), index=True)
    therapist_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("therapists.id"))
    start_date: Mapped[date]
    weeks: Mapped[int] = mapped_column(SmallInteger)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class ProgramItem(Base):
    """One exercise in a program, with its dose and frequency."""

    __tablename__ = "program_items"
    __table_args__ = (
        CheckConstraint("sets BETWEEN 1 AND 10", name="ck_program_items_sets"),
        CheckConstraint("reps BETWEEN 1 AND 100", name="ck_program_items_reps"),
        CheckConstraint("times_per_week BETWEEN 1 AND 14", name="ck_program_items_frequency"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    program_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("programs.id"), index=True)
    exercise_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("exercises.id"))
    sets: Mapped[int] = mapped_column(SmallInteger)
    reps: Mapped[int] = mapped_column(SmallInteger)
    times_per_week: Mapped[int] = mapped_column(SmallInteger)
    position: Mapped[int] = mapped_column(SmallInteger)


class ExerciseLog(Base):
    """A session checked off by the patient, at most once per exercise per day."""

    __tablename__ = "exercise_logs"
    __table_args__ = (
        CheckConstraint("pain_level BETWEEN 0 AND 10", name="ck_exercise_logs_pain"),
        UniqueConstraint("program_item_id", "done_on", name="uq_exercise_logs_once_per_day"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    program_item_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("program_items.id"), index=True)
    done_on: Mapped[date]  # the day in Montréal time
    done_at: Mapped[datetime] = mapped_column(server_default=func.now())
    pain_level: Mapped[int | None] = mapped_column(SmallInteger)
