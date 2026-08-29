"""Payment provider contract + value types. Amounts are paise (INR minor units)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class ProviderOrder:
    provider_order_id: str
    key_id: str
    amount_paise: int
    currency: str
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class WebhookEvent:
    event: str
    provider_event_id: str
    provider_order_id: str | None
    provider_subscription_id: str | None
    plan_id: str | None
    paid: bool
    raw: dict[str, Any] = field(default_factory=dict)


class PaymentProvider(Protocol):
    name: str

    async def create_order(
        self, *, amount_paise: int, currency: str, plan_id: str, receipt: str
    ) -> ProviderOrder: ...

    def verify_webhook(self, body: bytes, signature: str) -> WebhookEvent | None: ...
