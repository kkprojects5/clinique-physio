"""Exercise library, home programs and check-offs (B-EXE-01 to 04)."""

import uuid
from datetime import timedelta

import pytest
from sqlalchemy import select

from app.models import AuditLog, Exercise, ExerciseLog, Program, ProgramItem
from app.services.availability_service import today_local
from tests.test_clinical import as_staff, clinic, visit  # noqa: F401  (fixture)
from tests.test_login import make_user
from tests.test_schedules import make_patient, patient_headers

ME = "/api/v1/me/program"


def programs_url(patient):
    return f"/api/v1/therapist/patients/{patient.id}/programs"


def library(db):
    return db.scalars(select(Exercise).order_by(Exercise.name_en)).all()


def give(client, db, clinic, therapist=None, patient=None, start=None, weeks=4, **extra):
    exercises = library(db)[:2]
    body = {
        "start_date": str(start or today_local()),
        "weeks": weeks,
        "notes": "Faire les exercices le matin.",
        "items": [
            {"exercise_id": str(exercises[0].id), "times_per_week": 3},
            {"exercise_id": str(exercises[1].id), "sets": 2, "reps": 8, "times_per_week": 5},
        ],
        **extra,
    }
    return client.post(
        programs_url(patient or clinic["marie"]),
        json=body,
        headers=as_staff(therapist or clinic["anne"]),
    )


@pytest.fixture
def treated(db, clinic):
    """Anne treats Marie."""
    visit(db, clinic, clinic["anne"], clinic["marie"])
    return clinic


# --- Library (B-EXE-01) -------------------------------------------------------------


def test_the_library_is_public_and_bilingual(client):
    body = client.get("/api/v1/exercises").json()

    assert len(body) >= 8
    bridge = next(e for e in body if e["name_en"] == "Glute bridge")
    assert bridge["name_fr"] == "Pont fessier"
    assert bridge["instructions_fr"] and bridge["instructions_en"]


# --- Assigning a program (B-EXE-02) -------------------------------------------------


def test_a_therapist_gives_a_program_to_a_patient_they_treat(client, db, treated):
    response = give(client, db, treated)

    assert response.status_code == 201
    body = response.json()
    first, second = body["items"]
    assert (first["sets"], first["reps"]) == (
        library(db)[0].default_sets,
        library(db)[0].default_reps,
    )  # defaults of the exercise
    assert (second["sets"], second["reps"], second["times_per_week"]) == (2, 8, 5)
    assert first["planned_total"] == 3 * 4
    assert body["end_date"] == str(today_local() + timedelta(weeks=4))
    assert body["adherence_percent"] == 0
    [entry] = db.scalars(select(AuditLog).where(AuditLog.resource_type == "program")).all()
    assert (entry.action, entry.patient_id) == ("create", treated["marie"].id)


def test_no_program_for_a_patient_the_therapist_does_not_treat(client, db, treated):
    response = give(client, db, treated, therapist=treated["paul"])

    assert response.status_code == 404
    entry = db.scalars(select(AuditLog).where(AuditLog.actor_id == treated["paul"].user_id)).one()
    assert entry.action == "access_denied"


@pytest.mark.parametrize(
    "change,code",
    [
        ({"start_date": "2020-01-01"}, 409),  # in the past
        ({"weeks": 0}, 422),
        ({"weeks": 27}, 422),
        ({"items": []}, 422),
    ],
)
def test_invalid_programs_are_refused(client, db, treated, change, code):
    assert give(client, db, treated, **change).status_code == code


def test_same_exercise_twice_or_unknown_exercise_is_refused(client, db, treated):
    exercise = library(db)[0]
    twice = [{"exercise_id": str(exercise.id), "times_per_week": 3}] * 2
    unknown = [{"exercise_id": str(uuid.uuid4()), "times_per_week": 3}]

    assert give(client, db, treated, items=twice).status_code == 409
    assert give(client, db, treated, items=unknown).status_code == 409


@pytest.mark.parametrize("role", ["front_desk", "admin"])
def test_only_therapists_give_programs(client, db, treated, role):
    staff = make_user(db, f"{role}-{uuid.uuid4().hex[:6]}@example.com", role=role)
    url = programs_url(treated["marie"])

    assert client.get(url, headers=as_staff(staff, role=role)).status_code == 403
    assert client.get(url, headers=patient_headers(treated["marie"])).status_code == 403


# --- The patient's program (B-EXE-03) ------------------------------------------------


def test_the_patient_sees_the_program_in_progress(client, db, treated):
    give(client, db, treated)

    body = client.get(ME, headers=patient_headers(treated["marie"])).json()

    assert body["therapist"]["last_name"] == "Lefebvre"
    assert body["notes"] == "Faire les exercices le matin."
    assert len(body["items"]) == 2
    assert body["items"][0]["exercise"]["name_fr"]


def test_no_program_in_progress_gives_null(client, db, treated):
    give(client, db, treated, start=today_local() + timedelta(days=3))  # not started yet

    response = client.get(ME, headers=patient_headers(treated["marie"]))

    assert response.status_code == 200
    assert response.json() is None


def test_a_patient_never_sees_another_patients_program(client, db, treated):
    give(client, db, treated)

    other = client.get(ME, headers=patient_headers(make_patient(db, "Luc"))).json()

    assert other is None


def test_check_off_once_a_day_with_pain_level(client, db, treated):
    item = give(client, db, treated).json()["items"][0]
    headers = patient_headers(treated["marie"])
    url = f"{ME}/items/{item['id']}/check-off"

    first = client.post(url, json={"pain_level": 3}, headers=headers)
    again = client.post(url, json={"pain_level": 2}, headers=headers)

    assert first.status_code == 201
    assert first.json()["done_on"] == str(today_local())
    assert first.json()["pain_level"] == 3
    assert again.status_code == 409
    item_now = client.get(ME, headers=headers).json()["items"][0]
    assert (item_now["done_today"], item_now["done_this_week"], item_now["done_total"]) == (
        True,
        1,
        1,
    )


@pytest.mark.parametrize("pain", [-1, 11])
def test_pain_level_is_between_0_and_10(client, db, treated, pain):
    item = give(client, db, treated).json()["items"][0]

    response = client.post(
        f"{ME}/items/{item['id']}/check-off",
        json={"pain_level": pain},
        headers=patient_headers(treated["marie"]),
    )

    assert response.status_code == 422


def test_pain_level_is_optional(client, db, treated):
    item = give(client, db, treated).json()["items"][0]

    response = client.post(
        f"{ME}/items/{item['id']}/check-off", json={}, headers=patient_headers(treated["marie"])
    )

    assert response.status_code == 201
    assert response.json()["pain_level"] is None


def test_cannot_check_off_someone_elses_exercise(client, db, treated):
    item = give(client, db, treated).json()["items"][0]

    response = client.post(
        f"{ME}/items/{item['id']}/check-off",
        json={},
        headers=patient_headers(make_patient(db, "Luc")),
    )

    assert response.status_code == 404


def test_cannot_check_off_a_finished_program(client, db, treated):
    exercise = library(db)[0]
    old = Program(
        patient_id=treated["marie"].id,
        therapist_id=treated["anne"].id,
        start_date=today_local() - timedelta(weeks=5),
        weeks=4,
    )
    db.add(old)
    db.flush()
    item = ProgramItem(
        program_id=old.id, exercise_id=exercise.id, sets=3, reps=10, times_per_week=3, position=1
    )
    db.add(item)
    db.commit()

    response = client.post(
        f"{ME}/items/{item.id}/check-off", json={}, headers=patient_headers(treated["marie"])
    )

    assert response.status_code == 409


def test_undo_only_todays_check_off(client, db, treated):
    item = give(client, db, treated).json()["items"][0]
    headers = patient_headers(treated["marie"])
    today = client.post(f"{ME}/items/{item['id']}/check-off", json={}, headers=headers).json()
    yesterday = ExerciseLog(
        program_item_id=uuid.UUID(item["id"]), done_on=today_local() - timedelta(days=1)
    )
    db.add(yesterday)
    db.commit()

    assert client.delete(f"{ME}/check-offs/{yesterday.id}", headers=headers).status_code == 409
    other = patient_headers(make_patient(db, "Luc"))
    assert client.delete(f"{ME}/check-offs/{today['id']}", headers=other).status_code == 404
    assert client.delete(f"{ME}/check-offs/{today['id']}", headers=headers).status_code == 204
    assert client.get(ME, headers=headers).json()["items"][0]["done_today"] is False


# --- Adherence for the therapist (B-EXE-04) ------------------------------------------


def test_therapist_sees_adherence_and_the_read_is_audited(client, db, treated):
    program = give(client, db, treated).json()
    first = program["items"][0]
    client.post(
        f"{ME}/items/{first['id']}/check-off",
        json={"pain_level": 4},
        headers=patient_headers(treated["marie"]),
    )

    body = client.get(programs_url(treated["marie"]), headers=as_staff(treated["anne"])).json()

    [listed] = body
    planned = 3 * 4 + 5 * 4
    assert listed["adherence_percent"] == round(100 * 1 / planned)
    assert listed["items"][0]["done_total"] == 1
    actions = [
        a.action
        for a in db.scalars(select(AuditLog).where(AuditLog.resource_type == "program")).all()
    ]
    assert actions == ["create", "read"]


def test_therapist_without_care_relationship_cannot_see_programs(client, db, treated):
    give(client, db, treated)

    response = client.get(programs_url(treated["marie"]), headers=as_staff(treated["paul"]))

    assert response.status_code == 404
