"""Payments port. Routers call get_payment_provider(), never a vendor directly.

- "mock"     — in-process, no network (default; the only impl CI runs)
- "razorpay" — live Orders API + HMAC webhook, requires the RAZORPAY_* keys
"""

from __future__ import annotations

from app.config import get_settings
from app.services.payments.base import PaymentProvider, ProviderOrder, WebhookEvent
from app.services.payments.mock import MockPaymentProvider

REGISTERED_PROVIDERS = ("mock", "razorpay")


def validate_startup_config() -> None:
    s = get_settings()
    name = s.payments_provider.strip().lower()
    if name not in REGISTERED_PROVIDERS:
        raise RuntimeError(
            f"PAYMENTS_PROVIDER={name!r} is not registered. Options: {', '.join(REGISTERED_PROVIDERS)}."
        )
    if name == "razorpay" and not (
        s.razorpay_key_id and s.razorpay_key_secret and s.razorpay_webhook_secret
    ):
        raise RuntimeError(
            "PAYMENTS_PROVIDER=razorpay requires RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET, "
            "and RAZORPAY_WEBHOOK_SECRET."
        )


def get_payment_provider() -> PaymentProvider:
    if get_settings().payments_provider.strip().lower() == "razorpay":
        from app.services.payments.razorpay import RazorpayPaymentProvider

        return RazorpayPaymentProvider()
    return MockPaymentProvider()


__all__ = [
    "PaymentProvider",
    "ProviderOrder",
    "REGISTERED_PROVIDERS",
    "WebhookEvent",
    "get_payment_provider",
    "validate_startup_config",
]
