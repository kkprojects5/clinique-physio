"""Home exercise programs (B-EXE-01 to 04).

- The library of exercises is public (general descriptions, no patient data).
- A therapist gives a program only to a patient they treat (same care relationship as the
  clinical file, B-AUTH-05). Programs and check-offs are health data: every therapist read or
  write is audited, and refused attempts too.
- A program runs for a number of weeks from its start date. The patient sees the program in
  progress and checks off each exercise at most once a day (in Montréal time), with an
  optional pain level from 0 to 10. A check-off of today can be undone, never an older one.
- Adherence = sessions done / sessions planned (times per week x weeks), per exercise (B-EXE-04).
"""

import uuid
from dataclasses import dataclass
from datetime import date, timedelta

from fastapi import Request
from psycopg.errors import UniqueViolation
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    Exercise,
    ExerciseLog,
    Patient,
    Program,
    ProgramItem,
    Therapist,
)
from app.services import audit_service
from app.services.availability_service import today_local
from app.services.clinical_service import has_care_relationship

MAX_ITEMS = 20


class ExerciseError(Exception):
    status_code = 409


class NotFound(ExerciseError):
    status_code = 404

    def __init__(self) -> None:
        super().__init__("Not found.")


@dataclass
class ItemSpec:
    exercise_id: uuid.UUID
    sets: int | None
    reps: int | None
    times_per_week: int


@dataclass
class ItemView:
    item: ProgramItem
    exercise: Exercise
    done_total: int
    planned_total: int
    done_this_week: int
    done_today: bool


@dataclass
class ProgramView:
    program: Program
    therapist: Therapist
    items: list[ItemView]

    @property
    def end_date(self) -> date:
        return self.program.start_date + timedelta(weeks=self.program.weeks)

    @property
    def adherence_percent(self) -> int:
        planned = sum(i.planned_total for i in self.items)
        done = sum(i.done_total for i in self.items)
        return round(100 * done / planned) if planned else 0


def list_exercises(db: Session) -> list[Exercise]:
    return list(
        db.scalars(select(Exercise).where(Exercise.is_active).order_by(Exercise.name_fr)).all()
    )


def _deny(db, therapist, patient_id, request) -> NotFound:
    db.rollback()
    audit_service.log(db, therapist.user_id, "access_denied", "program", None, patient_id, request)
    db.commit()
    return NotFound()


def _view(db: Session, program: Program, today: date) -> ProgramView:
    week_start = today - timedelta(days=today.weekday())
    rows = db.execute(
        select(ProgramItem, Exercise)
        .join(Exercise, Exercise.id == ProgramItem.exercise_id)
        .where(ProgramItem.program_id == program.id)
        .order_by(ProgramItem.position)
    ).all()
    items = []
    for item, exercise in rows:
        days = set(
            db.scalars(select(ExerciseLog.done_on).where(ExerciseLog.program_item_id == item.id))
        )
        items.append(
            ItemView(
                item=item,
                exercise=exercise,
                done_total=len(days),
                planned_total=item.times_per_week * program.weeks,
                done_this_week=sum(1 for d in days if week_start <= d <= today),
                done_today=today in days,
            )
        )
    return ProgramView(program, db.get(Therapist, program.therapist_id), items)


def create_program(
    db: Session,
    therapist: Therapist,
    patient_id: uuid.UUID,
    start_date: date,
    weeks: int,
    notes: str | None,
    items: list[ItemSpec],
    request: Request | None = None,
) -> ProgramView:
    """Give a program to a patient I treat. Audited."""
    if db.get(Patient, patient_id) is None or not has_care_relationship(db, therapist, patient_id):
        raise _deny(db, therapist, patient_id, request)
    today = today_local()
    if start_date < today:
        raise ExerciseError("A program cannot start in the past.")
    if not 1 <= len(items) <= MAX_ITEMS:
        raise ExerciseError(f"A program has between 1 and {MAX_ITEMS} exercises.")
    if len({i.exercise_id for i in items}) != len(items):
        raise ExerciseError("Each exercise can appear only once in a program.")
    exercises = {
        e.id: e
        for e in db.scalars(
            select(Exercise).where(
                Exercise.id.in_([i.exercise_id for i in items]), Exercise.is_active
            )
        )
    }
    if len(exercises) != len(items):
        raise ExerciseError("Unknown exercise in the program.")

    program = Program(
        id=uuid.uuid4(),
        patient_id=patient_id,
        therapist_id=therapist.id,
        start_date=start_date,
        weeks=weeks,
        notes=(notes or "").strip() or None,
    )
    db.add(program)
    for position, spec in enumerate(items, start=1):
        exercise = exercises[spec.exercise_id]
        db.add(
            ProgramItem(
                program_id=program.id,
                exercise_id=exercise.id,
                sets=spec.sets or exercise.default_sets,
                reps=spec.reps or exercise.default_reps,
                times_per_week=spec.times_per_week,
                position=position,
            )
        )
    db.flush()
    audit_service.log(db, therapist.user_id, "create", "program", program.id, patient_id, request)
    db.commit()
    return _view(db, program, today)


def patient_programs(
    db: Session, therapist: Therapist, patient_id: uuid.UUID, request: Request | None = None
) -> list[ProgramView]:
    """Programs of a patient I treat, newest first, with adherence. Audited."""
    if not has_care_relationship(db, therapist, patient_id):
        raise _deny(db, therapist, patient_id, request)
    programs = db.scalars(
        select(Program)
        .where(Program.patient_id == patient_id)
        .order_by(Program.start_date.desc(), Program.created_at.desc())
    ).all()
    audit_service.log(db, therapist.user_id, "read", "program", None, patient_id, request)
    db.commit()
    today = today_local()
    return [_view(db, p, today) for p in programs]


def _current(db: Session, patient: Patient, today: date) -> Program | None:
    """The program in progress today: started, not finished; the newest if several."""
    end = Program.start_date + func.make_interval(0, 0, Program.weeks)
    return db.scalar(
        select(Program)
        .where(Program.patient_id == patient.id, Program.start_date <= today, end > today)
        .order_by(Program.start_date.desc(), Program.created_at.desc())
        .limit(1)
    )


def my_program(db: Session, patient: Patient) -> ProgramView | None:
    today = today_local()
    program = _current(db, patient, today)
    return _view(db, program, today) if program else None


def check_off(
    db: Session, patient: Patient, item_id: uuid.UUID, pain_level: int | None
) -> ExerciseLog:
    """Check off today's session of one exercise of my program in progress."""
    today = today_local()
    item = db.get(ProgramItem, item_id)
    program = db.get(Program, item.program_id) if item else None
    if program is None or program.patient_id != patient.id:
        raise NotFound
    current = _current(db, patient, today)
    if current is None or current.id != program.id:
        raise ExerciseError("This program is not in progress.")
    log = ExerciseLog(program_item_id=item.id, done_on=today, pain_level=pain_level)
    db.add(log)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        if isinstance(error.orig, UniqueViolation):
            raise ExerciseError("Already checked off today.") from None
        raise
    return log


def undo_today(db: Session, patient: Patient, log_id: uuid.UUID) -> None:
    """Remove my check-off of today (a mistake). Older check-offs stay as they are."""
    row = db.execute(
        select(ExerciseLog, Program)
        .join(ProgramItem, ProgramItem.id == ExerciseLog.program_item_id)
        .join(Program, Program.id == ProgramItem.program_id)
        .where(ExerciseLog.id == log_id)
    ).first()
    if row is None or row.Program.patient_id != patient.id:
        raise NotFound
    if row.ExerciseLog.done_on != today_local():
        raise ExerciseError("Only today's check-off can be undone.")
    db.delete(row.ExerciseLog)
    db.commit()
