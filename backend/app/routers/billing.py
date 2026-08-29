"""Checkout session + webhook (mvp-spec.md §7). No LLM, no quota. The webhook
path (HMAC verify + WebhookEvents idempotency + period anchor) is identical for
the mock and the live Razorpay provider."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas import CheckoutRequest
from app.services.billing import create_checkout_session, handle_webhook

router = APIRouter(prefix="/billing", tags=["billing"])


@router.post("/checkout-session")
async def checkout_session(
    body: CheckoutRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    return await create_checkout_session(db, user, body.plan_id)


@router.post("/webhook")
async def webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_razorpay_signature: str = Header(default="", alias="X-Razorpay-Signature"),
    x_signature: str = Header(default="", alias="X-Signature"),
) -> dict:
    body = await request.body()
    return await handle_webhook(db, body, x_razorpay_signature or x_signature)
