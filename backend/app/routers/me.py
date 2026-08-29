"""Profile + saved packages / hourly rate (mvp-spec.md §7). No LLM, no quota."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.models import Package, User
from app.schemas import MeUpdate, MeView, PackageOut, PlanOut, UsageOut
from app.services.quota import get_quota_state

router = APIRouter(prefix="/me", tags=["me"])


async def _view(db: AsyncSession, user: User) -> MeView:
    quota = await get_quota_state(db, user)
    packages = list(
        (
            await db.execute(
                select(Package).where(Package.user_id == user.id).order_by(Package.sort_order)
            )
        ).scalars()
    )
    return MeView(
        id=user.id,
        email=user.email,
        name=user.name,
        quote_currency=user.quote_currency,
        hourly_rate_minor=user.hourly_rate_minor,
        plan=PlanOut(
            id=user.plan.id,
            name=user.plan.name,
            proposals_included=user.plan.proposals_included,
        ),
        packages=[
            PackageOut(id=p.id, label=p.label, amount_minor=p.amount_minor, currency=p.currency)
            for p in packages
        ],
        usage=UsageOut(
            included=quota.included,
            used=quota.used,
            remaining=quota.remaining,
            period_end=quota.record.period_end,
        ),
    )


@router.get("", response_model=MeView)
async def get_me(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> MeView:
    return await _view(db, user)


@router.put("", response_model=MeView)
async def update_me(
    body: MeUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MeView:
    user.name = body.name
    user.quote_currency = body.quote_currency.value
    user.hourly_rate_minor = body.hourly_rate_minor

    # Upsert by label so package ids stay stable across profile edits — a
    # proposal's stored pricing_input references package ids, and editing a
    # price should not orphan it.
    existing = {
        p.label: p
        for p in (
            await db.execute(select(Package).where(Package.user_id == user.id))
        ).scalars()
    }
    kept_labels = {pkg.label for pkg in body.packages}
    for label, row in existing.items():
        if label not in kept_labels:
            await db.delete(row)
    for i, pkg in enumerate(body.packages):
        row = existing.get(pkg.label)
        if row is None:
            db.add(
                Package(
                    user_id=user.id,
                    label=pkg.label,
                    amount_minor=pkg.amount_minor,
                    currency=user.quote_currency,
                    sort_order=i,
                )
            )
        else:
            row.amount_minor = pkg.amount_minor
            row.currency = user.quote_currency
            row.sort_order = i
    await db.flush()
    return await _view(db, user)
