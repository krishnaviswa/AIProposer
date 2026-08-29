"""initial schema (S-001)

Revision ID: 0001_initial
Revises:
Create Date: 2026-08-29
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "plans",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("rail", sa.String(length=8), nullable=False),
        sa.Column("price_minor", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("proposals_included", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("overage_minor", sa.Integer(), nullable=True),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=True),
        sa.Column("quote_currency", sa.String(length=3), nullable=False, server_default="INR"),
        sa.Column("hourly_rate_minor", sa.Integer(), nullable=True),
        sa.Column("billing_country", sa.String(length=2), nullable=True),
        sa.Column("plan_id", sa.String(length=32), sa.ForeignKey("plans.id"), nullable=False, server_default="free"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "packages",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("amount_minor", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_packages_user_id", "packages", ["user_id"])

    op.create_table(
        "proposals",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("client_name", sa.String(length=200), nullable=False),
        sa.Column("client_company", sa.String(length=200), nullable=True),
        sa.Column("service_type", sa.String(length=20), nullable=False),
        sa.Column("brief_text", sa.String(length=1500), nullable=False),
        sa.Column("notes", sa.String(length=1000), nullable=True),
        sa.Column("pricing_mode", sa.String(length=16), nullable=False),
        sa.Column("pricing_input", sa.JSON(), nullable=False),
        sa.Column("tone", sa.String(length=16), nullable=False),
        sa.Column("language", sa.String(length=2), nullable=False, server_default="en"),
        sa.Column("status", sa.String(length=8), nullable=False, server_default="draft"),
        sa.Column("llm_input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("llm_output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("proposal_json", sa.JSON(), nullable=False),
        sa.Column("pdf_url", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_proposals_user_id", "proposals", ["user_id"])

    op.create_table(
        "usage_records",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("proposals_count", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("user_id", "period_start", name="uq_usage_user_period"),
    )
    op.create_index("ix_usage_records_user_id", "usage_records", ["user_id"])

    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("provider", sa.String(length=16), nullable=False, server_default="razorpay"),
        sa.Column("provider_customer_id", sa.String(length=64), nullable=True),
        sa.Column("provider_subscription_id", sa.String(length=64), nullable=True),
        sa.Column("plan_id", sa.String(length=32), sa.ForeignKey("plans.id"), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_subscriptions_user_id", "subscriptions", ["user_id"])

    op.create_table(
        "webhook_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("provider", sa.String(length=16), nullable=False),
        sa.Column("provider_event_id", sa.String(length=128), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("provider", "provider_event_id", name="uq_webhook_provider_event"),
    )


def downgrade() -> None:
    op.drop_table("webhook_events")
    op.drop_index("ix_subscriptions_user_id", "subscriptions")
    op.drop_table("subscriptions")
    op.drop_index("ix_usage_records_user_id", "usage_records")
    op.drop_table("usage_records")
    op.drop_index("ix_proposals_user_id", "proposals")
    op.drop_table("proposals")
    op.drop_index("ix_packages_user_id", "packages")
    op.drop_table("packages")
    op.drop_index("ix_users_email", "users")
    op.drop_table("users")
    op.drop_table("plans")
