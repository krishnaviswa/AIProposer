"""The pricing assembler — the ONLY place proposal money is decided.

Runs before the model on generate/regenerate. Every amount comes from the
user's own saved data: `packages.amount_minor` or `hourly_rate_minor × hours`
or a fee the user typed. No multiplier, no model input (mvp-spec.md §0.3, §9).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from fastapi import HTTPException, status

from app.models import Package, PricingMode, User


@dataclass
class PricingLine:
    label: str
    amount_minor: int
    currency: str


@dataclass
class AssembledPricing:
    lines: list[PricingLine]

    @property
    def labels(self) -> list[str]:
        return [line.label for line in self.lines]


def _fail(msg: str) -> None:
    raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, msg)


def assemble(
    *,
    user: User,
    packages: list[Package],
    pricing_mode: str,
    package_ids: list[uuid.UUID] | None = None,
    hourly: list[dict] | None = None,
    fixed: dict | None = None,
) -> AssembledPricing:
    currency = user.quote_currency

    if pricing_mode == PricingMode.packages.value:
        if not package_ids:
            _fail("packages mode needs at least one package_id")
        by_id = {p.id: p for p in packages}
        lines: list[PricingLine] = []
        for pid in package_ids:
            pkg = by_id.get(pid)
            if pkg is None:
                _fail(f"package {pid} is not one of your saved packages")
            lines.append(PricingLine(pkg.label, pkg.amount_minor, pkg.currency or currency))
        if len(lines) > 3:
            _fail("a proposal can have at most 3 package options")
        return AssembledPricing(lines)

    if pricing_mode == PricingMode.hourly.value:
        if user.hourly_rate_minor is None:
            _fail("hourly mode needs your hourly rate saved in the profile first")
        if not hourly:
            _fail("hourly mode needs at least one {label, hours} option")
        lines = []
        for opt in hourly:
            hours = opt.get("hours")
            label = str(opt.get("label") or "").strip()
            if not label or not isinstance(hours, (int, float)) or hours <= 0:
                _fail("each hourly option needs a label and positive hours")
            lines.append(
                PricingLine(label, int(round(user.hourly_rate_minor * hours)), currency)
            )
        if len(lines) > 3:
            _fail("a proposal can have at most 3 options")
        return AssembledPricing(lines)

    if pricing_mode == PricingMode.fixed.value:
        if not fixed:
            _fail("fixed mode needs {label, amount_minor}")
        label = str(fixed.get("label") or "").strip()
        amount = fixed.get("amount_minor")
        if not label or not isinstance(amount, int) or amount < 0:
            _fail("fixed mode needs a label and a non-negative integer amount_minor")
        return AssembledPricing([PricingLine(label, amount, currency)])

    _fail(f"unknown pricing_mode {pricing_mode!r}")
    raise AssertionError  # unreachable
