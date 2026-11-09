"""Exercise library (public) and home programs (B-EXE-01 to 04)."""

import uuid

from fastapi import APIRouter, HTTPException, Request, Response, status

from app.dependencies import CurrentPatient, CurrentTherapist, DbSession
from app.models import Exercise
from app.schemas.exercise import (
    CheckOffIn,
    CheckOffOut,
    ExerciseOut,
    ProgramIn,
    ProgramItemOut,
    ProgramOut,
)
from app.schemas.schedule import TherapistRef
from app.services import exercise_service

router = APIRouter(tags=["exercises"])


def _exercise(e: Exercise) -> ExerciseOut:
    return ExerciseOut.model_validate(e, from_attributes=True)


def _program(view: exercise_service.ProgramView) -> ProgramOut:
    p, t = view.program, view.therapist
    return ProgramOut(
        id=p.id,
        patient_id=p.patient_id,
        therapist=TherapistRef(id=t.id, first_name=t.first_name, last_name=t.last_name),
        start_date=p.start_date,
        end_date=view.end_date,
        weeks=p.weeks,
        notes=p.notes,
        adherence_percent=view.adherence_percent,
        items=[
            ProgramItemOut(
                id=i.item.id,
                exercise=_exercise(i.exercise),
                sets=i.item.sets,
                reps=i.item.reps,
                times_per_week=i.item.times_per_week,
                done_total=i.done_total,
                planned_total=i.planned_total,
                done_this_week=i.done_this_week,
                done_today=i.done_today,
            )
            for i in view.items
        ],
    )


def _refused(error: exercise_service.ExerciseError) -> HTTPException:
    return HTTPException(status_code=error.status_code, detail=str(error))


@router.get("/exercises")
def list_exercises(db: DbSession) -> list[ExerciseOut]:
    """The clinic's exercise library, in French and English."""
    return [_exercise(e) for e in exercise_service.list_exercises(db)]


@router.post("/therapist/patients/{patient_id}/programs", status_code=status.HTTP_201_CREATED)
def create_program(
    request: Request,
    patient_id: uuid.UUID,
    data: ProgramIn,
    db: DbSession,
    therapist: CurrentTherapist,
) -> ProgramOut:
    """Give a home program to a patient I treat. Audited."""
    items = [
        exercise_service.ItemSpec(i.exercise_id, i.sets, i.reps, i.times_per_week)
        for i in data.items
    ]
    try:
        view = exercise_service.create_program(
            db, therapist, patient_id, data.start_date, data.weeks, data.notes, items, request
        )
    except exercise_service.ExerciseError as error:
        raise _refused(error) from None
    return _program(view)


@router.get("/therapist/patients/{patient_id}/programs")
def list_patient_programs(
    request: Request, patient_id: uuid.UUID, db: DbSession, therapist: CurrentTherapist
) -> list[ProgramOut]:
    """Programs of a patient I treat, newest first, with adherence. Audited."""
    try:
        views = exercise_service.patient_programs(db, therapist, patient_id, request)
    except exercise_service.ExerciseError as error:
        raise _refused(error) from None
    return [_program(v) for v in views]


@router.get("/me/program")
def read_my_program(db: DbSession, patient: CurrentPatient) -> ProgramOut | None:
    """My program in progress today, or null if there is none."""
    view = exercise_service.my_program(db, patient)
    return _program(view) if view else None


@router.post("/me/program/items/{item_id}/check-off", status_code=status.HTTP_201_CREATED)
def check_off(
    item_id: uuid.UUID, data: CheckOffIn, db: DbSession, patient: CurrentPatient
) -> CheckOffOut:
    """I did this exercise today (once a day), with an optional pain level from 0 to 10."""
    try:
        log = exercise_service.check_off(db, patient, item_id, data.pain_level)
    except exercise_service.ExerciseError as error:
        raise _refused(error) from None
    return CheckOffOut(
        id=log.id,
        program_item_id=log.program_item_id,
        done_on=log.done_on,
        pain_level=log.pain_level,
    )


@router.delete("/me/program/check-offs/{log_id}", status_code=status.HTTP_204_NO_CONTENT)
def undo_check_off(log_id: uuid.UUID, db: DbSession, patient: CurrentPatient) -> Response:
    """Undo my check-off of today (a mistake). Older ones cannot be removed."""
    try:
        exercise_service.undo_today(db, patient, log_id)
    except exercise_service.ExerciseError as error:
        raise _refused(error) from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)
