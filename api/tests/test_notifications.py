"""Booking emails to the patient (B-BKG-01): confirmed, moved, cancelled. No clinical data."""

from datetime import UTC, datetime, timedelta

import pytest

from app.models import User
from app.services import notification_service
from tests.test_booking import at, clinic, place  # noqa: F401  (fixture)
from tests.test_clinical import as_staff
from tests.test_login import make_user
from tests.test_payments import (
    held_appointment,
    pay,
    send,
    stripe_event,
    stripe_fake,  # noqa: F401  (fixture)
)
from tests.test_schedules import make_patient, patient_headers


@pytest.fixture
def outbox(monkeypatch):
    sent = []
    monkeypatch.setattr(
        notification_service,
        "send_email",
        lambda to, subject, body: sent.append({"to": to, "subject": subject, "body": body}),
    )
    return sent


# --- Wording ------------------------------------------------------------------------------------


def test_time_is_written_in_montreal_time_in_both_languages():
    start = datetime(2026, 11, 24, 15, 0, tzinfo=UTC)  # 10:00 in Montréal (winter time)

    assert notification_service.when(start, "fr") == "mardi 24 novembre 2026 à 10 h 00"
    assert notification_service.when(start, "en") == "Tuesday, November 24, 2026 at 10:00 a.m."


def test_summer_time_and_afternoon():
    start = datetime(2026, 7, 6, 18, 30, tzinfo=UTC)  # 14:30 in Montréal (summer time)

    assert notification_service.when(start, "fr") == "lundi 6 juillet 2026 à 14 h 30"
    assert notification_service.when(start, "en") == "Monday, July 6, 2026 at 2:30 p.m."


def test_confirmation_has_practical_details_only(db, clinic):  # noqa: F811
    marie = make_patient(db, "Marie")
    appointment = place(db, marie, clinic["anne"], clinic["treatment"], at(10))

    email = notification_service.booking_email(db, appointment, "confirmed")

    assert email.to == db.get(User, marie.user_id).email
    assert email.subject.startswith("Rendez-vous confirmé")
    assert "Service : Traitement" in email.body
    assert "Physiothérapeute : " in email.body and "Lefebvre" in email.body
    assert "4200, rue Saint-Denis" in email.body
    assert "/mes-rendez-vous" in email.body and "24 heures" in email.body
    # Nothing clinical: no notes, no diagnosis, no reason for the visit.
    for word in ("note", "diagnos", "douleur", "SOAP"):
        assert word not in email.body.lower()


def test_email_follows_the_patient_language(db, clinic):  # noqa: F811
    marie = make_patient(db, "Marie")
    db.get(User, marie.user_id).language = "en"
    db.commit()
    appointment = place(db, marie, clinic["anne"], clinic["treatment"], at(10))

    email = notification_service.booking_email(db, appointment, "moved")

    assert email.subject.startswith("Appointment moved")
    assert "Service: Treatment" in email.body


def test_no_email_for_an_inactive_account(db, clinic):  # noqa: F811
    marie = make_patient(db, "Marie")
    db.get(User, marie.user_id).is_active = False
    db.commit()
    appointment = place(db, marie, clinic["anne"], clinic["treatment"], at(10))

    assert notification_service.booking_email(db, appointment, "confirmed") is None


# --- Sent at the right moments ------------------------------------------------------------------


def test_confirmation_sent_once_when_stripe_confirms(client, db, clinic, stripe_fake, outbox):  # noqa: F811
    marie, appointment_id = held_appointment(client, db, clinic)
    pay(client, marie, appointment_id)
    assert outbox == []  # nothing while the slot is only held

    send(client, stripe_event("payment_intent.succeeded", "pi_1"))
    send(client, stripe_event("payment_intent.succeeded", "pi_1"))  # Stripe sends it again

    assert len(outbox) == 1
    assert outbox[0]["subject"].startswith("Rendez-vous confirmé")


def test_failed_payment_sends_nothing(client, db, clinic, stripe_fake, outbox):  # noqa: F811
    marie, appointment_id = held_appointment(client, db, clinic)
    pay(client, marie, appointment_id)

    send(client, stripe_event("payment_intent.payment_failed", "pi_1"))

    assert outbox == []


def test_phone_booking_is_confirmed_by_email(client, db, clinic, outbox):  # noqa: F811
    desk = make_user(db, "accueil-mail@example.com", role="front_desk")
    marie = make_patient(db, "Marie")

    response = client.post(
        "/api/v1/desk/appointments",
        json={
            "patient_id": str(marie.id),
            "service_id": str(clinic["evaluation"].id),
            "therapist_id": str(clinic["anne"].id),
            "start": at(8).isoformat(),
        },
        headers=as_staff(desk, role="front_desk"),
    )

    assert response.status_code == 201
    assert [m["subject"][:21] for m in outbox] == ["Rendez-vous confirmé "]


def test_cancelling_a_paid_appointment_early_says_refunded(client, db, clinic, stripe_fake, outbox):  # noqa: F811
    marie, appointment_id = held_appointment(client, db, clinic)
    pay(client, marie, appointment_id)
    send(client, stripe_event("payment_intent.succeeded", "pi_1"))

    response = client.post(
        f"/api/v1/appointments/{appointment_id}/cancel", headers=patient_headers(marie)
    )

    assert response.status_code == 200
    cancelled = outbox[-1]
    assert cancelled["subject"].startswith("Rendez-vous annulé")
    assert "sera remboursé" in cancelled["body"]


def test_cancelling_without_online_payment_says_nothing_to_refund(client, db, clinic, outbox):  # noqa: F811
    marie = make_patient(db, "Marie")
    later = place(db, marie, clinic["anne"], clinic["treatment"], at(10) + timedelta(days=7))

    client.post(f"/api/v1/appointments/{later.id}/cancel", headers=patient_headers(marie))

    assert "rien à rembourser" in outbox[0]["body"]


def test_refused_change_sends_nothing(client, db, clinic, outbox):  # noqa: F811
    marie, other = make_patient(db, "Marie"), make_patient(db, "Paul")
    theirs = place(db, other, clinic["anne"], clinic["treatment"], at(10) + timedelta(days=7))

    response = client.post(
        f"/api/v1/appointments/{theirs.id}/cancel", headers=patient_headers(marie)
    )

    assert response.status_code == 404
    assert outbox == []


def test_queued_emails_appear_in_the_server_log_without_the_address():
    """Render's log shows that the email left, with a masked address and no body.

    The test sets the app's logging up again from scratch, because the test database
    migration (Alembic) resets logging; on Render, Alembic runs in its own process.
    """
    import io
    import logging

    from app.core.logging import setup_logging
    from app.services.email import send_email

    app_logger = logging.getLogger("app")
    email_logger = logging.getLogger("app.services.email")
    saved = (app_logger.handlers[:], app_logger.level, app_logger.disabled, email_logger.disabled)
    app_logger.handlers = []
    app_logger.disabled = email_logger.disabled = False
    try:
        setup_logging()
        output = io.StringIO()
        app_logger.handlers[0].setStream(output)
        send_email("marie.tremblay@example.com", "Rendez-vous confirmé", "secret body")
    finally:
        app_logger.handlers, app_logger.level, app_logger.disabled, email_logger.disabled = saved

    log = output.getvalue()
    assert "INFO" in log and "m***@example.com" in log and "Rendez-vous confirmé" in log
    assert "marie.tremblay" not in log and "secret body" not in log
