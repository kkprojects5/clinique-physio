"""Stripe webhook (B-BKG-04): Stripe tells us the result of a payment.

No login here: trust comes only from Stripe's signature, checked with the endpoint's secret,
and each event is applied once.
"""

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request, status

from app.dependencies import DbSession
from app.services import notification_service, payment_service
from app.services.stripe_gateway import InvalidWebhook, StripeGateway, get_gateway

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    db: DbSession,
    gateway: Annotated[StripeGateway, Depends(get_gateway)],
    background: BackgroundTasks,
    stripe_signature: Annotated[str | None, Header()] = None,
) -> dict[str, str]:
    payload = await request.body()
    try:
        event = gateway.parse_webhook(payload, stripe_signature)
    except InvalidWebhook:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid webhook."
        ) from None
    outcome = payment_service.handle_event(db, event, gateway)
    if outcome == "confirmed":
        email = notification_service.confirmed_by_payment(db, event.object_id)
        background.add_task(notification_service.send, email)
    return {"received": "true", "outcome": outcome}
