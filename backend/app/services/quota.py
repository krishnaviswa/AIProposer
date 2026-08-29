"""Usage-period + quota logic (mvp-spec.md §3.1, §6).

One UsageRecord per (user, period). The period is anchored to the subscription
for paid plans, or a rolling FREE_PERIOD_DAYS window from the user's created_at
for Free. The counter increments only when a generation is actually saved —
that write happens in generation.py inside the same transaction.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import Subscription, UsageRecord, User


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


@dataclass
class QuotaState:
    record: UsageRecord
    included: int
    used: int

    @property
    def remaining(self) -> int:
        return max(0, self.included - self.used)

    @property
    def over(self) -> bool:
        return self.used >= self.included


async def _current_window(db: AsyncSession, user: User) -> tuple[datetime, datetime]:
    settings = get_settings()
    sub = (
        await db.execute(
            select(Subscription)
            .where(Subscription.user_id == user.id, Subscription.status == "active")
            .order_by(Subscription.current_period_end.desc())
        )
    ).scalars().first()

    now = _now()
    if sub and sub.current_period_end:
        end = _aware(sub.current_period_end)
        start = end - timedelta(days=settings.free_period_days)
        while end < now:  # roll forward if the anchor lapsed
            start, end = end, end + timedelta(days=settings.free_period_days)
        return start, end

    anchor = _aware(user.created_at)
    length = timedelta(days=settings.free_period_days)
    periods = max(0, (now - anchor) // length)
    start = anchor + periods * length
    return start, start + length


async def get_quota_state(db: AsyncSession, user: User) -> QuotaState:
    start, end = await _current_window(db, user)
    record = (
        await db.execute(
            select(UsageRecord).where(
                UsageRecord.user_id == user.id, UsageRecord.period_start == start
            )
        )
    ).scalar_one_or_none()
    if record is None:
        record = UsageRecord(user_id=user.id, period_start=start, period_end=end, proposals_count=0)
        db.add(record)
        await db.flush()
    return QuotaState(record=record, included=user.plan.proposals_included, used=record.proposals_count)


async def ensure_within_quota(db: AsyncSession, user: User) -> QuotaState:
    state = await get_quota_state(db, user)
    if state.over:
        raise HTTPException(
            status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "error": "quota_exhausted",
                "included": state.included,
                "used": state.used,
                "hint": "Upgrade to the Starter plan for a higher monthly limit.",
            },
        )
    return state


async def reanchor_period(db: AsyncSession, user: User) -> None:
    """After a plan change — make sure the next quota check builds a fresh window."""
    await get_quota_state(db, user)
