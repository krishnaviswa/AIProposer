"""Checkout session + webhook (mvp-spec.md §7). No LLM, no quota. Wave 3 = mock
payment adapter; the webhook path (HMAC + idempotency + anchor) is real."""

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
    x_signature: str = Header(default=""),
) -> dict:
    body = await request.body()
    return await handle_webhook(db, body, x_signature)
