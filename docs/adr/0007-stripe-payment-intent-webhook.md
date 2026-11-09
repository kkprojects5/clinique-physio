# ADR-0007: Deposit payment with a Stripe PaymentIntent confirmed by a signed webhook

- Status: Accepted (D2)
- Requirements: B-BKG-03, B-BKG-04, B-BKG-06

## Context

Patients pay a deposit online when they book; the slot is held 10 minutes meanwhile. The clinic
must never handle card numbers (PCI DSS scope), a payment must never be counted twice, nobody
may fake a payment confirmation, and a patient must never pay for an appointment they do not get.

## Decision

1. **PaymentIntent.** `POST /appointments/{id}/pay` creates a Stripe PaymentIntent for the
   deposit (test mode, CAD) with an idempotency key `deposit-<appointment id>`: calling it again
   returns the same intent. The website shows Stripe's card form with the intent's client
   secret, so **card details go straight from the browser to Stripe**; our API never sees them.
   The hold gets 10 more minutes, once (`held` → `pending_payment`).
2. **Webhook as the only source of truth.** The appointment is confirmed only when Stripe's
   webhook `payment_intent.succeeded` arrives, never because the browser says so.
   `POST /webhooks/stripe` verifies Stripe's signature and its timestamp (5-minute tolerance,
   against replays) with the endpoint's signing secret, before reading anything.
3. **Exactly once.** Each event id is stored in `payment_events` (unique). A repeated event is
   recorded once and changes nothing.
4. **No payment without an appointment.** If the payment succeeds after the hold expired or
   after a cancellation, the deposit is refunded automatically.
5. **Refunds.** Cancelling more than 24 hours before refunds the deposit through Stripe before
   the cancellation is saved; if Stripe refuses, nothing is cancelled and the patient can retry.
6. **One gateway class** (`app/services/stripe_gateway.py`) is the only code that talks to
   Stripe. Tests replace it with a fake (no network, no keys); the signature check stays real.

## Alternatives considered

- **Stripe Checkout (hosted page).** Less code, but the patient leaves the site and comes back;
  the PaymentIntent flow keeps the booking on one page. Both keep cards out of our systems.
- **Confirm from the browser's success callback.** Rejected: a modified browser could claim a
  payment that never happened.
- **Store the full webhook payload.** Rejected: only the event id and type are needed
  (data minimization, Law 25).

## Consequences

- No card data in our systems; Stripe holds it (lowest PCI scope).
- Requires the webhook to be configured: locally with the Stripe CLI (`stripe listen`), in
  production as an endpoint in the Stripe dashboard pointing to the API, with its signing secret
  in the host's settings.
- Without Stripe keys, online payment answers 503 and the rest of the API keeps working.
- Proven by `api/tests/test_payments.py` (signature, replay, idempotency, late payment refund,
  refund on cancellation, failed refund).
