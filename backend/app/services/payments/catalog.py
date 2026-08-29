"""Plan catalog in code (mvp-spec.md §5.1, §6). v0 ships Free + India Starter.

`price_minor` is paise for the INR rail. These rows are also seeded into the
`plans` table by scripts/seed.py — this dict is the source of truth for both.
"""

from __future__ import annotations

PLANS: dict[str, dict] = {
    "free": {
        "id": "free",
        "name": "Free",
        "rail": "usd",
        "price_minor": 0,
        "proposals_included": 3,
        "overage_minor": None,
        "checkout": False,
    },
    "starter_inr": {
        "id": "starter_inr",
        "name": "Starter (India)",
        "rail": "inr",
        "price_minor": 50000,  # ₹500, GST-inclusive (mvp-spec.md §5.1)
        "proposals_included": 20,
        "overage_minor": None,
        "checkout": True,
    },
}

DEFAULT_PLAN_ID = "free"


class UnknownPlanError(KeyError):
    pass


def get_plan(plan_id: str) -> dict:
    try:
        return PLANS[plan_id]
    except KeyError as exc:
        raise UnknownPlanError(plan_id) from exc


def checkout_plans() -> list[dict]:
    return [dict(p) for p in PLANS.values() if p["checkout"]]
