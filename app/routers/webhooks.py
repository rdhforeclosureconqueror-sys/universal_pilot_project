from __future__ import annotations

import hashlib
import hmac
import json
import os
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.services.payment_service import PaymentProcessingError, handle_successful_payment
from db.session import get_db


router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def _verify_signature(payload: bytes, signature_header: str | None, secret: str) -> bool:
    if not signature_header:
        return False

    values = {}
    for item in signature_header.split(","):
        if "=" in item:
            key, value = item.split("=", 1)
            values[key] = value

    timestamp = values.get("t")
    signature = values.get("v1")
    if not timestamp or not signature:
        return False

    signed_payload = f"{timestamp}.{payload.decode('utf-8')}"
    expected = hmac.new(secret.encode("utf-8"), signed_payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    db: Session = Depends(get_db),
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
):
    secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    if not secret:
        raise HTTPException(status_code=500, detail="Stripe webhook secret is not configured")

    payload = await request.body()
    if not _verify_signature(payload, stripe_signature, secret):
        raise HTTPException(status_code=400, detail="Invalid Stripe signature")

    event: dict[str, Any] = json.loads(payload.decode("utf-8"))
    if event.get("type") != "invoice.payment_succeeded":
        return {"status": "ignored"}

    obj = event.get("data", {}).get("object", {})
    stripe_invoice_id = obj.get("id")
    stripe_customer_id = obj.get("customer")
    amount_paid_cents = obj.get("amount_paid")

    if not stripe_invoice_id or not stripe_customer_id or amount_paid_cents is None:
        raise HTTPException(status_code=400, detail="Missing required Stripe invoice payload fields")

    try:
        handle_successful_payment(
            db=db,
            stripe_invoice_id=str(stripe_invoice_id),
            stripe_customer_id=str(stripe_customer_id),
            amount_paid_cents=int(amount_paid_cents),
        )
    except PaymentProcessingError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return {"status": "ok"}
