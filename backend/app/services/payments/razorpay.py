"""Live Razorpay provider (mvp-spec.md §7, §18.1).

Orders API over HTTPS (Basic auth key_id:key_secret). Webhook verified with
HMAC-SHA256 hex of the raw body against the `X-Razorpay-Signature` header —
same scheme the mock uses, so `billing.handle_webhook` is unchanged.

The user + plan travel in the order `notes`, which Razorpay echoes back on the
webhook (`payload.order.entity.notes`).
"""

from __future__ import annotations

from typing import Any

import httpx

from app.config import get_settings
from app.services.payments.base import ProviderOrder, WebhookEvent
from app.services.payments.hmac_util import loads_json, signatures_match

_PAID_EVENTS = {"order.paid", "payment.captured", "subscription.charged", "subscription.activated"}


class RazorpayPaymentProvider:
    name = "razorpay"

    def __init__(self) -> None:
        s = get_settings()
        self._base = s.razorpay_api_base.rstrip("/")
        self._auth = (s.razorpay_key_id, s.razorpay_key_secret)
        self._webhook_secret = s.razorpay_webhook_secret
        self.key_id = s.razorpay_key_id

    async def create_order(
        self, *, amount_paise: int, currency: str, plan_id: str, receipt: str, notes: dict[str, str]
    ) -> ProviderOrder:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{self._base}/orders",
                auth=self._auth,
                json={
                    "amount": amount_paise,
                    "currency": currency,
                    "receipt": receipt,
                    "notes": {**notes, "plan_id": plan_id},
                },
            )
        resp.raise_for_status()
        data = resp.json()
        return ProviderOrder(
            provider_order_id=data["id"],
            key_id=self.key_id,
            amount_paise=int(data["amount"]),
            currency=data.get("currency", currency),
            extra={"receipt": receipt, "status": data.get("status")},
        )

    def verify_webhook(self, body: bytes, signature: str) -> WebhookEvent | None:
        if not signatures_match(self._webhook_secret, body, signature):
            return None
        try:
            payload = loads_json(body)
        except (ValueError, UnicodeDecodeError):
            return None

        event = str(payload.get("event") or "")
        entities: dict[str, Any] = payload.get("payload") or {}
        order = (entities.get("order") or {}).get("entity") or {}
        payment = (entities.get("payment") or {}).get("entity") or {}
        subscription = (entities.get("subscription") or {}).get("entity") or {}
        notes = order.get("notes") or payment.get("notes") or subscription.get("notes") or {}
        if order.get("receipt"):
            notes = {**notes, "receipt": order["receipt"]}

        return WebhookEvent(
            event=event,
            provider_event_id=str(
                payload.get("id") or payment.get("id") or order.get("id") or event
            ),
            provider_order_id=order.get("id") or payment.get("order_id"),
            provider_subscription_id=subscription.get("id"),
            plan_id=notes.get("plan_id"),
            notes=notes,
            paid=event in _PAID_EVENTS,
            raw=payload,
        )
