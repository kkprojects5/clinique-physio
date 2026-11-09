"""Deposit payment with Stripe and refunds (B-BKG-04, B-BKG-06).

Stripe itself is replaced by a fake gateway (no network, no keys). The webhook signature is
checked for real, with Stripe's own verification and a test secret.
"""

import hashlib
import hmac
import json
import time
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.main import app
from app.models import Appointment, Payment, PaymentEvent, User
from app.services import booking_service
from app.services.stripe_gateway import Intent, PaymentError, StripeGateway, get_gateway
from tests.test_booking import at, clinic, hold, place  # noqa: F401  (fixture)
from tests.test_schedules import make_patient, patient_headers

WEBHOOK_SECRET = "whsec_test_only_not_a_real_secret"
WEBHOOK = "/api/v1/webhooks/stripe"


class FakeStripe(StripeGateway):
    """Records calls instead of contacting Stripe. Webhook verification stays real."""

    def __init__(self, enabled=True):
        super().__init__("", WEBHOOK_SECRET)
        self._enabled = enabled
        self.intents: dict[str, Intent] = {}
        self.keys: dict[str, str] = {}
        self.refunds: list[str] = []
        self.fail = False

    @property
    def enabled(self):
        return self._enabled

    def create_deposit_intent(self, amount_cents, appointment_id, idempotency_key):
        if self.fail:
            raise PaymentError("card network down")
        if idempotency_key in self.keys:  # like Stripe: same key, same intent
            return self.intents[self.keys[idempotency_key]]
        intent = Intent(f"pi_{len(self.intents) + 1}", f"pi_{len(self.intents) + 1}_secret", "x")
        self.intents[intent.id] = intent
        self.keys[idempotency_key] = intent.id
        self.amount = amount_cents
        return intent

    def retrieve_intent(self, intent_id):
        return self.intents[intent_id]

    def refund(self, intent_id, idempotency_key):
        if self.fail:
            raise PaymentError("refund refused")
        self.refunds.append(intent_id)
        return f"re_{len(self.refunds)}", "succeeded"


@pytest.fixture
def stripe_fake():
    fake = FakeStripe()
    app.dependency_overrides[get_gateway] = lambda: fake
    yield fake
    app.dependency_overrides.pop(get_gateway, None)


def signed(event: dict, secret: str = WEBHOOK_SECRET, at_time: int | None = None):
    payload = json.dumps(event).encode()
    timestamp = at_time or int(time.time())
    digest = hmac.new(secret.encode(), f"{timestamp}.".encode() + payload, hashlib.sha256)
    return payload, {"Stripe-Signature": f"t={timestamp},v1={digest.hexdigest()}"}


def stripe_event(event_type: str, intent_id: str, event_id: str = "evt_1") -> dict:
    return {
        "id": event_id,
        "object": "event",
        "type": event_type,
        "data": {"object": {"id": intent_id, "object": "payment_intent"}},
    }


def send(client, event, **kwargs):
    payload, headers = signed(event, **kwargs)
    return client.post(WEBHOOK, content=payload, headers=headers)


def held_appointment(client, db, clinic):
    marie = make_patient(db, "Marie")
    body = hold(client, marie, clinic["evaluation"], at(8), clinic["anne"]).json()
    return marie, body["id"]


def pay(client, patient, appointment_id):
    return client.post(
        f"/api/v1/appointments/{appointment_id}/pay", headers=patient_headers(patient)
    )


# --- Starting the payment ------------------------------------------------------------


def test_paying_a_hold_creates_a_deposit_intent(client, db, clinic, stripe_fake):
    marie, appointment_id = held_appointment(client, db, clinic)

    response = pay(client, marie, appointment_id)

    assert response.status_code == 200
    body = response.json()
    assert body["client_secret"] == "pi_1_secret"
    assert body["amount_cents"] == 3000 == stripe_fake.amount  # the evaluation's deposit
    assert body["currency"] == "cad"
    assert body["appointment"]["status"] == "pending_payment"
    payment = db.scalar(select(Payment))
    assert (payment.type, payment.status, payment.stripe_id) == ("deposit", "pending", "pi_1")


def test_paying_again_reuses_the_same_intent(client, db, clinic, stripe_fake):
    marie, appointment_id = held_appointment(client, db, clinic)

    first = pay(client, marie, appointment_id).json()
    second = pay(client, marie, appointment_id).json()

    assert first["client_secret"] == second["client_secret"]
    assert len(db.scalars(select(Payment)).all()) == 1


def test_the_hold_is_extended_once_when_payment_starts(client, db, clinic, stripe_fake):
    marie, appointment_id = held_appointment(client, db, clinic)
    appointment = db.get(Appointment, appointment_id)
    appointment.hold_expires_at = datetime.now(UTC) + timedelta(minutes=1)
    db.commit()

    pay(client, marie, appointment_id)
    db.refresh(appointment)
    extended = appointment.hold_expires_at
    pay(client, marie, appointment_id)
    db.refresh(appointment)

    assert extended - datetime.now(UTC) > timedelta(minutes=9)
    assert appointment.hold_expires_at == extended  # not extended a second time


def test_cannot_pay_after_the_hold_expired(client, db, clinic, stripe_fake):
    marie, appointment_id = held_appointment(client, db, clinic)
    appointment = db.get(Appointment, appointment_id)
    appointment.hold_expires_at = datetime.now(UTC) - timedelta(seconds=1)
    db.commit()

    response = pay(client, marie, appointment_id)

    assert response.status_code == 409
    assert stripe_fake.intents == {}


def test_cannot_pay_someone_elses_appointment(client, db, clinic, stripe_fake):
    _, appointment_id = held_appointment(client, db, clinic)

    response = pay(client, make_patient(db, "Luc"), appointment_id)

    assert response.status_code == 404
    assert stripe_fake.intents == {}


def test_confirmed_appointment_needs_no_payment(client, db, clinic, stripe_fake):
    marie = make_patient(db, "Marie")
    appointment = place(db, marie, clinic["anne"], clinic["evaluation"], at(8))

    assert pay(client, marie, appointment.id).status_code == 409


def test_payment_switched_off_without_stripe_keys(client, db, clinic):
    app.dependency_overrides[get_gateway] = lambda: FakeStripe(enabled=False)
    try:
        marie, appointment_id = held_appointment(client, db, clinic)
        response = pay(client, marie, appointment_id)
    finally:
        app.dependency_overrides.pop(get_gateway, None)

    assert response.status_code == 503


def test_stripe_error_gives_502_and_changes_nothing(client, db, clinic, stripe_fake):
    marie, appointment_id = held_appointment(client, db, clinic)
    stripe_fake.fail = True

    response = pay(client, marie, appointment_id)

    assert response.status_code == 502
    assert db.get(Appointment, appointment_id).status == "held"
    assert db.scalars(select(Payment)).all() == []


# --- The webhook -------------------------------------------------------------------


def test_payment_succeeded_confirms_the_appointment(client, db, clinic, stripe_fake):
    marie, appointment_id = held_appointment(client, db, clinic)
    pay(client, marie, appointment_id)

    response = send(client, stripe_event("payment_intent.succeeded", "pi_1"))

    assert response.status_code == 200
    assert response.json()["outcome"] == "confirmed"
    appointment = db.get(Appointment, appointment_id)
    db.refresh(appointment)
    assert appointment.status == "confirmed"
    assert appointment.hold_expires_at is None
    assert db.scalar(select(Payment)).status == "succeeded"


def test_the_same_event_twice_is_applied_once(client, db, clinic, stripe_fake):
    marie, appointment_id = held_appointment(client, db, clinic)
    pay(client, marie, appointment_id)
    event = stripe_event("payment_intent.succeeded", "pi_1")

    send(client, event)
    again = send(client, event)

    assert again.json()["outcome"] == "duplicate"
    assert len(db.scalars(select(PaymentEvent)).all()) == 1


def test_a_fake_or_altered_webhook_is_refused(client, db, clinic, stripe_fake):
    marie, appointment_id = held_appointment(client, db, clinic)
    pay(client, marie, appointment_id)
    event = stripe_event("payment_intent.succeeded", "pi_1")

    wrong_secret = send(client, event, secret="whsec_attacker")
    no_signature = client.post(WEBHOOK, content=json.dumps(event).encode())
    payload, headers = signed(event)
    altered = client.post(WEBHOOK, content=payload.replace(b"pi_1", b"pi_2"), headers=headers)
    replayed = send(client, event, at_time=int(time.time()) - 3600)  # an hour-old signature

    for response in (wrong_secret, no_signature, altered, replayed):
        assert response.status_code == 400
    db.refresh(db.get(Appointment, appointment_id))
    assert db.get(Appointment, appointment_id).status == "pending_payment"


def test_failed_payment_keeps_the_hold_and_can_be_retried(client, db, clinic, stripe_fake):
    marie, appointment_id = held_appointment(client, db, clinic)
    pay(client, marie, appointment_id)

    send(client, stripe_event("payment_intent.payment_failed", "pi_1"))
    retry = pay(client, marie, appointment_id)

    assert db.get(Appointment, appointment_id).status == "pending_payment"
    assert retry.json()["client_secret"] == "pi_1_secret"  # same intent, new card
    assert db.scalar(select(Payment)).status == "pending"


def test_payment_after_the_hold_expired_is_refunded(client, db, clinic, stripe_fake):
    marie, appointment_id = held_appointment(client, db, clinic)
    pay(client, marie, appointment_id)
    appointment = db.get(Appointment, appointment_id)
    booking_service.record(db, appointment, "expired", None, "test: hold expired")
    db.commit()

    response = send(client, stripe_event("payment_intent.succeeded", "pi_1"))

    assert response.json()["outcome"] == "refunded"
    assert stripe_fake.refunds == ["pi_1"]
    refund = db.scalar(select(Payment).where(Payment.type == "refund"))
    assert (refund.status, refund.amount_cents) == ("succeeded", 3000)
    assert db.get(Appointment, appointment_id).status == "expired"


def test_unknown_event_types_are_recorded_and_ignored(client, db, stripe_fake):
    response = send(client, stripe_event("customer.created", "cus_1", "evt_9"))

    assert response.json()["outcome"] == "ignored"
    assert db.scalar(select(PaymentEvent)).processed_at is not None


# --- Refund on cancellation (B-BKG-06) ------------------------------------------------


def paid_appointment(client, db, clinic, stripe_fake):
    marie, appointment_id = held_appointment(client, db, clinic)
    pay(client, marie, appointment_id)
    send(client, stripe_event("payment_intent.succeeded", "pi_1"))
    return marie, appointment_id


def cancel(client, patient, appointment_id):
    return client.post(
        f"/api/v1/appointments/{appointment_id}/cancel", headers=patient_headers(patient)
    )


def test_cancel_more_than_24h_before_refunds_through_stripe(client, db, clinic, stripe_fake):
    marie, appointment_id = paid_appointment(client, db, clinic, stripe_fake)

    response = cancel(client, marie, appointment_id)

    assert response.json()["deposit_refunded"] is True
    assert stripe_fake.refunds == ["pi_1"]
    assert db.scalar(select(Payment).where(Payment.type == "refund")) is not None


def test_cancel_less_than_24h_before_keeps_the_deposit(client, db, clinic, stripe_fake):
    marie, appointment_id = paid_appointment(client, db, clinic, stripe_fake)
    user = db.get(User, marie.user_id)
    start = db.get(Appointment, appointment_id).during.lower

    _, refunded = booking_service.cancel(
        db, marie, user, appointment_id, now=start - timedelta(hours=2), refund=lambda a: None
    )

    assert refunded is False
    assert stripe_fake.refunds == []


def test_a_failed_refund_cancels_nothing(client, db, clinic, stripe_fake):
    marie, appointment_id = paid_appointment(client, db, clinic, stripe_fake)
    stripe_fake.fail = True

    response = cancel(client, marie, appointment_id)

    assert response.status_code == 502
    assert "nothing was cancelled" in response.json()["detail"]
    db.expire_all()
    assert db.get(Appointment, appointment_id).status == "confirmed"


def test_demo_appointment_without_online_payment_cancels_without_refund(
    client, db, clinic, stripe_fake
):
    marie = make_patient(db, "Marie")
    appointment = place(db, marie, clinic["anne"], clinic["evaluation"], at(8))

    response = cancel(client, marie, appointment.id)

    assert response.status_code == 200
    assert stripe_fake.refunds == []
