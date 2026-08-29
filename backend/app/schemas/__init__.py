"""Pydantic request/response models.

The proposal RESPONSE is `ProposalView` — a curated DTO. `proposal_json` is
never a response body (mvp-spec.md §0.4, §15).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import (
    Currency,
    PricingMode,
    Proposal,
    ProposalStatus,
    ServiceType,
    Tone,
    User,
)

# --------------------------------------------------------------------------- me


class PackageIn(BaseModel):
    label: str = Field(min_length=1, max_length=120)
    amount_minor: int = Field(ge=0)


class PackageOut(PackageIn):
    id: uuid.UUID
    currency: str


class MeUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    quote_currency: Currency
    hourly_rate_minor: int | None = Field(default=None, ge=0)
    packages: list[PackageIn] = Field(default_factory=list, max_length=3)


class PlanOut(BaseModel):
    id: str
    name: str
    proposals_included: int


class UsageOut(BaseModel):
    included: int
    used: int
    remaining: int
    period_end: datetime


class MeView(BaseModel):
    id: uuid.UUID
    email: str
    name: str | None
    quote_currency: str
    hourly_rate_minor: int | None
    plan: PlanOut
    packages: list[PackageOut]
    usage: UsageOut


# --------------------------------------------------------------------- proposals


class HourlyOption(BaseModel):
    label: str = Field(min_length=1, max_length=120)
    hours: float = Field(gt=0)


class FixedOption(BaseModel):
    label: str = Field(min_length=1, max_length=120)
    amount_minor: int = Field(ge=0)


class ProposalCreate(BaseModel):
    client_name: str = Field(min_length=1, max_length=200)
    client_company: str | None = Field(default=None, max_length=200)
    service_type: ServiceType
    brief_text: str = Field(min_length=1, max_length=1500)
    notes: str | None = Field(default=None, max_length=1000)
    tone: Tone
    pricing_mode: PricingMode
    package_ids: list[uuid.UUID] | None = Field(default=None, max_length=3)
    hourly: list[HourlyOption] | None = Field(default=None, max_length=3)
    fixed: FixedOption | None = None

    @field_validator("package_ids")
    @classmethod
    def _nonempty(cls, v: list[uuid.UUID] | None) -> list[uuid.UUID] | None:
        if v is not None and len(v) == 0:
            raise ValueError("package_ids cannot be empty")
        return v


class PricingLineOut(BaseModel):
    label: str
    amount_minor: int
    currency: str
    justification: str = ""


class TimelineItem(BaseModel):
    label: str
    detail: str


class ProposalSections(BaseModel):
    executive_summary: str
    scope_of_work: list[str]
    timeline: list[TimelineItem]
    terms: list[str]
    followup_email: str


class ProposalView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    client_name: str
    client_company: str | None
    service_type: str
    tone: str
    pricing_mode: str
    status: str
    language: str
    pdf_url: str | None
    created_at: datetime
    updated_at: datetime
    sections: ProposalSections | None
    pricing: list[PricingLineOut]

    @classmethod
    def from_model(cls, p: Proposal) -> "ProposalView":
        pj = p.proposal_json or {}
        sections = None
        if pj.get("executive_summary"):
            sections = ProposalSections(
                executive_summary=pj.get("executive_summary", ""),
                scope_of_work=pj.get("scope_of_work", []),
                timeline=[TimelineItem(**t) for t in pj.get("timeline", [])],
                terms=pj.get("terms", []),
                followup_email=pj.get("followup_email", ""),
            )
        pricing = [
            PricingLineOut(
                label=line["label"],
                amount_minor=line["amount_minor"],
                currency=line["currency"],
                justification=line.get("justification", ""),
            )
            for line in pj.get("pricing", [])
        ]
        return cls(
            id=p.id,
            client_name=p.client_name,
            client_company=p.client_company,
            service_type=p.service_type,
            tone=p.tone,
            pricing_mode=p.pricing_mode,
            status=p.status,
            language=p.language,
            pdf_url=p.pdf_url,
            created_at=p.created_at,
            updated_at=p.updated_at,
            sections=sections,
            pricing=pricing,
        )


class _PatchSections(BaseModel):
    model_config = ConfigDict(extra="forbid")

    executive_summary: str | None = None
    scope_of_work: list[str] | None = None
    timeline: list[TimelineItem] | None = None
    terms: list[str] | None = None
    followup_email: str | None = None


class _PatchPricingLine(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str | None = Field(default=None, max_length=120)
    amount_minor: int | None = Field(default=None, ge=0)


class ProposalPatch(BaseModel):
    # `extra="forbid"` is what makes AC-13 (unknown key -> 422) work.
    model_config = ConfigDict(extra="forbid")

    client_name: str | None = Field(default=None, min_length=1, max_length=200)
    client_company: str | None = Field(default=None, max_length=200)
    status: ProposalStatus | None = None
    sections: _PatchSections | None = None
    pricing: list[_PatchPricingLine] | None = None


class CheckoutRequest(BaseModel):
    plan_id: str


__all__ = [
    "CheckoutRequest",
    "FixedOption",
    "HourlyOption",
    "MeUpdate",
    "MeView",
    "PackageIn",
    "PackageOut",
    "ProposalCreate",
    "ProposalPatch",
    "ProposalView",
    "User",
]
