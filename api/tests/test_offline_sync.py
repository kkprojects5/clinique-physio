"""Challenge B-C5: front desk offline, patient online, conflict detected and resolved.

Rule: the server's state wins. An offline action is applied only if the appointment is still
in the status the desk saw; otherwise it is a conflict, reported to the desk and audited.
"""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.models import Appointment, AuditLog, User
from app.schemas.schedule import SyncAction
from app.services import front_desk_service
from tests.test_booking import at, cancel_url, clinic, place  # noqa: F401  (fixture)
from tests.test_front_desk import desk, headers, marie, today_at  # noqa: F401  (fixtures)
from tests.test_schedules import patient_headers

SYNC = "/api/v1/desk/sync"


def offline(appointment, action="check_in", seen="confirmed", done_at=None):
    return {
        "id": str(uuid.uuid4()),
        "appointment_id": str(appointment.id),
        "action": action,
        "seen_status": seen,
        "done_at": (done_at or datetime.now(UTC)).isoformat(),
    }


def test_offline_check_in_is_applied_when_nothing_changed(client, db, desk, marie, clinic):  # noqa: F811
    appointment = place(db, marie, clinic["anne"], clinic["evaluation"], today_at(12))
    action = offline(appointment)

    response = client.post(SYNC, json={"actions": [action]}, headers=headers(desk))

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": action["id"],
            "appointment_id": str(appointment.id),
            "result": "applied",
            "status": "checked_in",
            "detail": None,
        }
    ]


def test_patient_cancels_online_while_the_desk_checks_in_offline(client, db, desk, marie, clinic):  # noqa: F811
    """The scenario of the specification, end to end through the API."""
    appointment = place(
        db, marie, clinic["anne"], clinic["evaluation"], datetime.now(UTC) + timedelta(hours=3)
    )
    # 1. The desk loses the connection, sees "confirmed" and clicks Check-in: kept offline.
    action = offline(appointment, done_at=datetime.now(UTC))
    # 2. Meanwhile the patient cancels on the website.
    cancelled = client.post(cancel_url(appointment.id), headers=patient_headers(marie))
    assert cancelled.status_code == 200

    # 3. The connection returns: the desk sends its offline actions.
    result = client.post(SYNC, json={"actions": [action]}, headers=headers(desk)).json()[0]

    # 4. Conflict detected and reported; the server's state (cancelled) is kept.
    assert result["result"] == "conflict"
    assert result["status"] == "cancelled_by_patient"
    assert "not applied" in result["detail"]
    db.expire_all()
    assert db.get(Appointment, appointment.id).status == "cancelled_by_patient"
    entry = db.scalar(select(AuditLog).where(AuditLog.action == "sync_conflict"))
    assert entry.actor_id == desk.id and entry.patient_id == marie.id


def test_sending_the_same_actions_twice_does_nothing_more(client, db, desk, marie, clinic):  # noqa: F811
    appointment = place(db, marie, clinic["anne"], clinic["evaluation"], today_at(12))
    body = {"actions": [offline(appointment)]}
    client.post(SYNC, json=body, headers=headers(desk))

    again = client.post(SYNC, json=body, headers=headers(desk)).json()[0]

    assert again["result"] == "already_done"


def test_time_rules_still_apply_at_the_moment_of_the_click(db, desk, marie, clinic):  # noqa: F811
    start = at(8)
    appointment = place(db, marie, clinic["anne"], clinic["evaluation"], start)
    user = db.get(User, desk.id)
    too_early = SyncAction(**offline(appointment, "no_show", done_at=start + timedelta(minutes=5)))

    outcome = front_desk_service.sync_offline_actions(
        db, user, [too_early], now=start + timedelta(hours=1)
    )

    assert outcome[0].result == "refused" and "15 minutes" in outcome[0].detail
    assert db.get(Appointment, appointment.id).status == "confirmed"


def test_an_action_older_than_12_hours_is_refused(db, desk, marie, clinic):  # noqa: F811
    appointment = place(db, marie, clinic["anne"], clinic["evaluation"], at(8))
    user = db.get(User, desk.id)
    stale = SyncAction(**offline(appointment, done_at=at(7)))

    outcome = front_desk_service.sync_offline_actions(
        db, user, [stale], now=at(7) + timedelta(hours=13)
    )

    assert outcome[0].result == "refused"


def test_actions_are_applied_in_the_order_they_were_done(db, desk, marie, clinic):  # noqa: F811
    """Check-in at 7:55, then (wrongly) no-show at 8:20: the second one finds 'checked_in'."""
    appointment = place(db, marie, clinic["anne"], clinic["evaluation"], at(8))
    user = db.get(User, desk.id)
    later = SyncAction(**offline(appointment, "no_show", done_at=at(8, 20)))
    first = SyncAction(**offline(appointment, done_at=at(7, 55)))

    outcomes = front_desk_service.sync_offline_actions(db, user, [later, first], now=at(9))

    assert [o.result for o in outcomes] == ["applied", "conflict"]
    assert db.get(Appointment, appointment.id).status == "checked_in"


def test_unknown_appointment_is_refused(client, db, desk):  # noqa: F811
    action = offline(type("Ghost", (), {"id": uuid.uuid4()})())

    result = client.post(SYNC, json={"actions": [action]}, headers=headers(desk)).json()[0]

    assert result["result"] == "refused"


def test_only_the_desk_can_send_offline_actions(client, db, marie, clinic):  # noqa: F811
    appointment = place(db, marie, clinic["anne"], clinic["evaluation"], today_at(12))

    response = client.post(
        SYNC, json={"actions": [offline(appointment)]}, headers=patient_headers(marie)
    )

    assert response.status_code == 403
