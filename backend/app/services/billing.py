"""Checkout + webhook handling (mvp-spec.md §7).

Wave 3 is a stub over the mock payment adapter — no real Razorpay. The webhook
path itself is real: HMAC verify + WebhookEvents idempotency + plan/period anchor.
The webhook identifies the user via the `receipt` we set on the order
("user:<uuid>"), which the mock echoes back in `raw`.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Subscription, User, WebhookEvent
from app.services.payments import get_payment_provider
from app.services.payments.base import WebhookEvent as WebhookEventDTO
from app.services.payments.catalog import UnknownPlanError, get_plan
from app.services.quota import reanchor_period


async def create_checkout_session(db: AsyncSession, user: User, plan_id: str) -> dict:
    try:
        plan = get_plan(plan_id)
    except UnknownPlanError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"unknown plan {plan_id!r}")
    if not plan["checkout"]:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"plan {plan_id!r} is not purchasable")

    order = await get_payment_provider().create_order(
        amount_paise=plan["price_minor"],
        currency="INR" if plan["rail"] == "inr" else "USD",
        plan_id=plan_id,
        receipt=f"user:{user.id}",
    )
    return {
        "provider_order_id": order.provider_order_id,
        "key_id": order.key_id,
        "amount_paise": order.amount_paise,
        "currency": order.currency,
        "plan_id": plan_id,
    }


def _user_id_from_event(event: WebhookEventDTO) -> uuid.UUID | None:
    raw = event.raw or {}
    ref = raw.get("receipt") or (raw.get("notes") or {}).get("receipt") or ""
    if isinstance(ref, str) and ref.startswith("user:"):
        try:
            return uuid.UUID(ref.split("user:", 1)[1])
        except ValueError:
            return None
    return None


async def handle_webhook(db: AsyncSession, body: bytes, signature: str) -> dict:
    provider = get_payment_provider()
    event = provider.verify_webhook(body, signature)
    if event is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "invalid webhook signature")

    db.add(
        WebhookEvent(
            provider=provider.name,
            provider_event_id=event.provider_event_id or event.event,
        )
    )
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        return {"received": True, "duplicate": True}

    if not event.paid or not event.plan_id:
        return {"received": True, "applied": False}

    try:
        plan = get_plan(event.plan_id)
    except UnknownPlanError:
        return {"received": True, "applied": False, "reason": "unknown plan"}

    user_id = _user_id_from_event(event)
    user = (
        (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
        if user_id
        else None
    )
    if user is None:
        return {"received": True, "applied": False, "reason": "no user ref"}

    now = datetime.now(timezone.utc)
    sub = (
        await db.execute(select(Subscription).where(Subscription.user_id == user.id))
    ).scalar_one_or_none()
    if sub is None:
        sub = Subscription(user_id=user.id, provider=provider.name, plan_id=plan["id"])
        db.add(sub)
    sub.plan_id = plan["id"]
    sub.status = "active"
    sub.provider_subscription_id = event.provider_subscription_id
    sub.current_period_end = now + timedelta(days=30)

    user.plan_id = plan["id"]
    await db.flush()
    await db.refresh(user)
    await reanchor_period(db, user)
    return {"received": True, "applied": True, "plan_id": plan["id"]}
