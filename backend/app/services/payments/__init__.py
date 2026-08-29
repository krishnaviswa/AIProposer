"""Payments port. Routers call get_payment_provider(), never Razorpay directly.

Wave 3: only the mock provider. Real Razorpay is Wave 4 — PAYMENTS_PROVIDER
!= "mock" fails at boot.
"""

from __future__ import annotations

from app.config import get_settings
from app.services.payments.base import PaymentProvider, ProviderOrder, WebhookEvent
from app.services.payments.mock import MockPaymentProvider

REGISTERED_PROVIDERS = ("mock",)


def validate_startup_config() -> None:
    name = get_settings().payments_provider.strip().lower()
    if name not in REGISTERED_PROVIDERS:
        raise RuntimeError(
            f"PAYMENTS_PROVIDER={name!r} is not available in this build. Real Razorpay lands in "
            f"Wave 4; registered now: {', '.join(REGISTERED_PROVIDERS)}."
        )


def get_payment_provider() -> PaymentProvider:
    validate_startup_config()
    return MockPaymentProvider()


__all__ = [
    "PaymentProvider",
    "ProviderOrder",
    "WebhookEvent",
    "get_payment_provider",
    "validate_startup_config",
]
