"""The only place that talks to Stripe (test mode). Tests replace it with a fake.

Card details never pass through our API: the website sends them straight to Stripe with the
PaymentIntent's client secret, and Stripe tells us the result through a signed webhook.
"""

from dataclasses import dataclass

import stripe

from app.core.config import settings


class PaymentError(Exception):
    """Stripe could not be reached or refused the request."""


class InvalidWebhook(Exception):
    """The webhook body or signature is not valid: it did not come from Stripe."""


@dataclass
class Intent:
    id: str
    client_secret: str
    status: str


@dataclass
class WebhookEvent:
    id: str
    type: str
    object_id: str


class StripeGateway:
    def __init__(self, secret_key: str, webhook_secret: str) -> None:
        self._client = stripe.StripeClient(secret_key) if secret_key else None
        self._webhook_secret = webhook_secret

    @property
    def enabled(self) -> bool:
        return self._client is not None

    def create_deposit_intent(
        self, amount_cents: int, appointment_id: str, idempotency_key: str
    ) -> Intent:
        """A PaymentIntent for the deposit. The same key always returns the same intent."""
        try:
            intent = self._client.v1.payment_intents.create(
                params={
                    "amount": amount_cents,
                    "currency": settings.currency,
                    "automatic_payment_methods": {"enabled": True},
                    "metadata": {"appointment_id": appointment_id, "type": "deposit"},
                    "description": "Dépôt / deposit — Clinique Physio Mont-Royal",
                },
                options={"idempotency_key": idempotency_key},
            )
        except stripe.StripeError as error:
            raise PaymentError(str(error.user_message or "Stripe error")) from error
        return Intent(intent.id, intent.client_secret, intent.status)

    def retrieve_intent(self, intent_id: str) -> Intent:
        try:
            intent = self._client.v1.payment_intents.retrieve(intent_id)
        except stripe.StripeError as error:
            raise PaymentError(str(error.user_message or "Stripe error")) from error
        return Intent(intent.id, intent.client_secret, intent.status)

    def refund(self, intent_id: str, idempotency_key: str) -> tuple[str, str]:
        """Refund a payment in full. Returns (refund id, status)."""
        try:
            refund = self._client.v1.refunds.create(
                params={"payment_intent": intent_id}, options={"idempotency_key": idempotency_key}
            )
        except stripe.StripeError as error:
            raise PaymentError(str(error.user_message or "Stripe error")) from error
        return refund.id, refund.status

    def parse_webhook(self, payload: bytes, signature: str | None) -> WebhookEvent:
        """Check Stripe's signature (and its timestamp, against replays) before trusting it."""
        if not self._webhook_secret:
            raise InvalidWebhook("Webhook secret not configured.")
        try:
            event = stripe.Webhook.construct_event(payload, signature, self._webhook_secret)
        except (ValueError, stripe.SignatureVerificationError) as error:
            raise InvalidWebhook("Invalid webhook.") from error
        return WebhookEvent(event.id, event.type, event.data.object.id)


def get_gateway() -> StripeGateway:
    return StripeGateway(settings.stripe_secret_key, settings.stripe_webhook_secret)
