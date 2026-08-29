"""Deterministic mock provider — stands in for the real model until Wave 4.

Returns structured copy derived from the payload so the whole pipeline
(validate, price-strip, persist, quota) is exercisable without a network call.

Test sentinels in the brief:
  __FAIL__               -> raise AIGenerationError (proves the 0-quota path)
  __MODEL_TRIES_PRICE__  -> stuff an `amount_minor` into the raw payload, to
                            prove the server strips it
"""

from __future__ import annotations

from decimal import Decimal

from app.services.ai.base import (
    AIGenerationError,
    AIProvider,
    ProposalCopyResult,
    ProposalPromptInput,
    TokenUsage,
)

_SERVICE_LABEL = {
    "web_dev": "web development",
    "design": "design",
    "video": "video production",
    "marketing": "marketing",
    "consulting": "consulting",
    "other": "professional services",
}


class MockAIProvider(AIProvider):
    name = "mock"

    async def generate_proposal_copy(self, payload: ProposalPromptInput) -> ProposalCopyResult:
        if "__FAIL__" in payload.brief_text:
            raise AIGenerationError("mock provider: forced failure sentinel")

        service = _SERVICE_LABEL.get(payload.service_type, "professional services")
        who = payload.client_company or payload.client_name
        brief_snip = " ".join(payload.brief_text.split()[:25]) or "the described engagement"

        summary = (
            f"Proposal for {who}: a {payload.tone} plan to deliver {service} work. "
            f"Scope is drawn from your brief — {brief_snip}."
        )
        scope = [
            f"Discovery and requirements review with {payload.client_name}",
            f"Core {service} delivery as described in the brief",
            "One round of revisions and handover",
        ]
        timeline = [
            {"label": "Week 1", "detail": "Kickoff, discovery, sign-off on scope"},
            {"label": "Weeks 2-3", "detail": f"{service.capitalize()} build"},
            {"label": "Week 4", "detail": "Revisions, QA, handover"},
        ]
        terms = [
            "50% on acceptance of this proposal, balance on delivery.",
            "Scope changes are quoted separately before work proceeds.",
            "Deliverables are released on receipt of final payment.",
        ]
        followup = (
            f"Hi {payload.client_name},\n\nFollowing up on the proposal for the {service} work. "
            f"Happy to walk through any of the options on a quick call.\n\nBest regards"
        )
        justifications = {
            label: f"The {label} option covers the {service} scope agreed for {who}."
            for label in payload.package_labels
        }

        raw = {"provider": "mock"}
        if "__MODEL_TRIES_PRICE__" in payload.brief_text:
            # A misbehaving model trying to set money. The server must ignore this.
            raw["pricing"] = [{"label": lbl, "amount_minor": 999999} for lbl in payload.package_labels]

        return ProposalCopyResult(
            executive_summary=summary,
            scope_of_work=scope,
            timeline=timeline,
            terms=terms,
            followup_email=followup,
            pricing_justifications=justifications,
            usage=TokenUsage(prompt_tokens=len(payload.brief_text.split()), completion_tokens=180),
            estimated_cost_usd=Decimal("0"),
            provider="mock",
            raw=raw,
        )
