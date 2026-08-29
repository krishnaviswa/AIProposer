"""Generate / regenerate orchestration.

Order is load-bearing (docs/architecture-sequences.md §3, docs/ai-touchpoints.md):
quota -> assemble prices (BEFORE the model) -> ingress scrub -> provider ->
egress validate + OVERWRITE prices with server values -> persist + increment,
all in one transaction. Any failure => 502, no row, no quota consumed.
"""

from __future__ import annotations

import asyncio
import uuid
from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Package, Proposal, ProposalStatus, User
from app.services import ingress, pricing
from app.services.ai import get_ai_provider
from app.services.ai.base import AIGenerationError, ProposalPromptInput
from app.services.quota import ensure_within_quota

# Best-effort single-flight per user (mvp-spec.md §16 "max concurrent LLM 1 per
# user"). In-process only — a distributed lock is Wave 4 / roadmap.
_user_locks: dict[uuid.UUID, asyncio.Lock] = defaultdict(asyncio.Lock)


@dataclass
class GenerationInputs:
    client_name: str
    client_company: str | None
    service_type: str
    brief_text: str
    notes: str | None
    tone: str
    pricing_mode: str
    package_ids: list[uuid.UUID] | None = None
    hourly: list[dict] | None = None
    fixed: dict | None = None


def _content_ok(pj: dict) -> bool:
    return bool(
        pj.get("executive_summary", "").strip()
        and pj.get("scope_of_work")
        and pj.get("pricing")
        and all(line.get("label") and isinstance(line.get("amount_minor"), int) for line in pj["pricing"])
    )


async def run_generation(
    db: AsyncSession,
    user: User,
    inputs: GenerationInputs,
    *,
    existing: Proposal | None = None,
) -> Proposal:
    async with _user_locks[user.id]:
        quota = await ensure_within_quota(db, user)

        packages = list(
            (await db.execute(select(Package).where(Package.user_id == user.id))).scalars()
        )
        assembled = pricing.assemble(
            user=user,
            packages=packages,
            pricing_mode=inputs.pricing_mode,
            package_ids=inputs.package_ids,
            hourly=inputs.hourly,
            fixed=inputs.fixed,
        )

        clean_brief, brief_flags = ingress.scrub(inputs.brief_text)
        clean_notes, note_flags = ingress.scrub(inputs.notes or "")

        payload = ProposalPromptInput(
            service_type=inputs.service_type,
            tone=inputs.tone,
            client_name=inputs.client_name,
            client_company=inputs.client_company,
            brief_text=clean_brief,
            notes=clean_notes or None,
            package_labels=assembled.labels,
        )

        try:
            result = await get_ai_provider().generate_proposal_copy(payload)
        except AIGenerationError:
            raise
        except Exception as exc:  # any provider blow-up is a generation failure
            raise AIGenerationError(str(exc)) from exc

        # Egress: server owns money. Model contributes justification + prose only.
        proposal_json = {
            "executive_summary": result.executive_summary,
            "scope_of_work": list(result.scope_of_work),
            "timeline": [dict(t) for t in result.timeline],
            "terms": list(result.terms),
            "followup_email": result.followup_email,
            "pricing": [
                {
                    "label": line.label,
                    "amount_minor": line.amount_minor,   # SERVER value
                    "currency": line.currency,           # SERVER value
                    "justification": result.pricing_justifications.get(line.label, ""),
                }
                for line in assembled.lines
            ],
            "_ingress_flags": brief_flags + note_flags,
        }
        if not _content_ok(proposal_json):
            raise AIGenerationError("generated copy failed the content check")

        pricing_input = {
            "mode": inputs.pricing_mode,
            "package_ids": [str(pid) for pid in (inputs.package_ids or [])] or None,
            "hourly": inputs.hourly,
            "fixed": inputs.fixed,
        }

        if existing is None:
            proposal = Proposal(
                user_id=user.id,
                client_name=inputs.client_name,
                client_company=inputs.client_company,
                service_type=inputs.service_type,
                brief_text=inputs.brief_text,
                notes=inputs.notes,
                pricing_mode=inputs.pricing_mode,
                pricing_input=pricing_input,
                tone=inputs.tone,
                status=ProposalStatus.draft.value,
            )
            db.add(proposal)
        else:
            proposal = existing
            proposal.pricing_input = pricing_input

        proposal.proposal_json = proposal_json
        proposal.pdf_url = None
        proposal.llm_input_tokens = result.usage.prompt_tokens
        proposal.llm_output_tokens = result.usage.completion_tokens

        quota.record.proposals_count += 1
        await db.flush()
        await db.refresh(proposal)
        return proposal
