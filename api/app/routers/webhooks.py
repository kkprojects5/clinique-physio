"""Stripe webhook (B-BKG-04): Stripe tells us the result of a payment.

No login here: trust comes only from Stripe's signature, checked with the endpoint's secret,
and each event is applied once.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status

from app.dependencies import DbSession
from app.services import payment_service
from app.services.stripe_gateway import InvalidWebhook, StripeGateway, get_gateway

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    db: DbSession,
    gateway: Annotated[StripeGateway, Depends(get_gateway)],
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
    return {"received": "true", "outcome": outcome}
