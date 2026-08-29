"""Seed the plan catalog (mvp-spec.md §5.1). Idempotent — safe to run on boot.

Run: PYTHONPATH=. python scripts/seed.py
"""

from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.database import get_sessionmaker
from app.models import Plan
from app.services.payments.catalog import PLANS


async def seed() -> None:
    async with get_sessionmaker()() as db:
        for spec in PLANS.values():
            existing = (
                await db.execute(select(Plan).where(Plan.id == spec["id"]))
            ).scalar_one_or_none()
            if existing is None:
                db.add(
                    Plan(
                        id=spec["id"],
                        name=spec["name"],
                        rail=spec["rail"],
                        price_minor=spec["price_minor"],
                        proposals_included=spec["proposals_included"],
                        overage_minor=spec["overage_minor"],
                    )
                )
            else:
                existing.name = spec["name"]
                existing.rail = spec["rail"]
                existing.price_minor = spec["price_minor"]
                existing.proposals_included = spec["proposals_included"]
                existing.overage_minor = spec["overage_minor"]
        await db.commit()
    print(f"seeded {len(PLANS)} plans: {', '.join(PLANS)}")


if __name__ == "__main__":
    asyncio.run(seed())
