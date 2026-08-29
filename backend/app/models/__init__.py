"""Logical schema per mvp-spec.md §6. Portable types (Uuid, JSON) so the same
models run on Postgres (prod / CI) and aiosqlite (test suite)."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Currency(str, enum.Enum):
    USD = "USD"
    INR = "INR"
    EUR = "EUR"
    GBP = "GBP"


class ServiceType(str, enum.Enum):
    web_dev = "web_dev"
    design = "design"
    video = "video"
    marketing = "marketing"
    consulting = "consulting"
    other = "other"


class Tone(str, enum.Enum):
    formal = "formal"
    friendly = "friendly"
    persuasive = "persuasive"


class PricingMode(str, enum.Enum):
    packages = "packages"
    hourly = "hourly"
    fixed = "fixed"


class ProposalStatus(str, enum.Enum):
    draft = "draft"
    sent = "sent"
    won = "won"
    lost = "lost"


class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(64))
    rail: Mapped[str] = mapped_column(String(8))  # inr | usd
    price_minor: Mapped[int] = mapped_column(Integer, default=0)
    proposals_included: Mapped[int] = mapped_column(Integer, default=0)
    overage_minor: Mapped[int | None] = mapped_column(Integer, nullable=True)


class User(Base):
    __tablename__ = "users"

    # = Supabase JWT `sub`
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    email: Mapped[str] = mapped_column(String(320), index=True)
    name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    quote_currency: Mapped[str] = mapped_column(String(3), default=Currency.INR.value)
    hourly_rate_minor: Mapped[int | None] = mapped_column(Integer, nullable=True)
    billing_country: Mapped[str | None] = mapped_column(String(2), nullable=True)
    plan_id: Mapped[str] = mapped_column(ForeignKey("plans.id"), default="free")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    plan: Mapped[Plan] = relationship(lazy="selectin")
    packages: Mapped[list["Package"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="Package.sort_order",
        lazy="selectin",
    )


class Package(Base):
    __tablename__ = "packages"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    label: Mapped[str] = mapped_column(String(120))
    amount_minor: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    user: Mapped[User] = relationship(back_populates="packages")


class Proposal(Base):
    __tablename__ = "proposals"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    client_name: Mapped[str] = mapped_column(String(200))
    client_company: Mapped[str | None] = mapped_column(String(200), nullable=True)
    service_type: Mapped[str] = mapped_column(String(20))
    brief_text: Mapped[str] = mapped_column(String(1500))
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    pricing_mode: Mapped[str] = mapped_column(String(16))
    # The pricing INPUT refs (package ids / hours / fee) chosen at create time.
    # Amounts are never stored here — they are re-derived from the user's saved
    # data on every generate/regenerate. Server only.
    pricing_input: Mapped[dict] = mapped_column(JSON, default=dict)
    tone: Mapped[str] = mapped_column(String(16))
    language: Mapped[str] = mapped_column(String(2), default="en")
    status: Mapped[str] = mapped_column(String(8), default=ProposalStatus.draft.value)
    llm_input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    llm_output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    # SERVER ONLY — never serialized to a client (mvp-spec.md §0.4, §15).
    proposal_json: Mapped[dict] = mapped_column(JSON, default=dict)
    pdf_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


class UsageRecord(Base):
    __tablename__ = "usage_records"
    __table_args__ = (UniqueConstraint("user_id", "period_start", name="uq_usage_user_period"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    proposals_count: Mapped[int] = mapped_column(Integer, default=0)


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    provider: Mapped[str] = mapped_column(String(16), default="razorpay")
    provider_customer_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    provider_subscription_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    plan_id: Mapped[str] = mapped_column(ForeignKey("plans.id"))
    status: Mapped[str] = mapped_column(String(32), default="active")
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class WebhookEvent(Base):
    __tablename__ = "webhook_events"
    __table_args__ = (
        UniqueConstraint("provider", "provider_event_id", name="uq_webhook_provider_event"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    provider: Mapped[str] = mapped_column(String(16))
    provider_event_id: Mapped[str] = mapped_column(String(128))
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


__all__ = [
    "Base",
    "Currency",
    "Package",
    "Plan",
    "PricingMode",
    "Proposal",
    "ProposalStatus",
    "ServiceType",
    "Subscription",
    "Tone",
    "UsageRecord",
    "User",
    "WebhookEvent",
]
