"""In-process mock gateway. No network. HMAC is still required on webhooks —
the mock signs and verifies with the same secret the real provider would use,
so the webhook code path is real (mvp-spec.md §18.1)."""

from __future__ import annotations

import uuid

from app.config import get_settings
from app.services.payments.base import ProviderOrder, WebhookEvent
from app.services.payments.hmac_util import loads_json, signatures_match


class MockPaymentProvider:
    name = "mock"

    def __init__(self) -> None:
        settings = get_settings()
        self.webhook_secret = settings.razorpay_webhook_secret
        self.key_id = settings.razorpay_key_id or "rzp_test_mock"

    async def create_order(
        self, *, amount_paise: int, currency: str, plan_id: str, receipt: str
    ) -> ProviderOrder:
        return ProviderOrder(
            provider_order_id=f"order_mock_{uuid.uuid4().hex[:16]}",
            key_id=self.key_id,
            amount_paise=amount_paise,
            currency=currency,
            extra={"receipt": receipt, "plan_id": plan_id},
        )

    def verify_webhook(self, body: bytes, signature: str) -> WebhookEvent | None:
        if not signatures_match(self.webhook_secret, body, signature):
            return None
        try:
            payload = loads_json(body)
        except (ValueError, UnicodeDecodeError):
            return None
        event = str(payload.get("event") or "")
        return WebhookEvent(
            event=event,
            provider_event_id=str(payload.get("id") or payload.get("event_id") or ""),
            provider_order_id=payload.get("order_id"),
            provider_subscription_id=payload.get("subscription_id"),
            plan_id=payload.get("plan_id"),
            paid=event in {"order.paid", "subscription.charged", "subscription.activated"},
            raw=payload,
        )
