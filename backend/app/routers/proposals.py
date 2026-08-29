"""Proposals CRUD + generate/regenerate/duplicate + PDF stub.

Generate & regenerate are the only endpoints that touch the AI port (a mock in
Wave 3). PATCH / list / detail / duplicate / pdf never call it and never consume
quota (docs/ai-touchpoints.md).

NOTE: no `from __future__ import annotations` here on purpose — slowapi's
`@limiter.limit` wraps the handler, and FastAPI then resolves string
annotations against slowapi's module globals, misclassifying the request body.
Real annotation objects avoid that.
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.rate_limit import generate_rate_key, limiter
from app.database import get_db
from app.deps import get_current_user, get_owned_proposal
from app.models import Proposal, ProposalStatus, User
from app.schemas import ProposalCreate, ProposalPatch, ProposalView
from app.services.ai.base import AIGenerationError
from app.services.generation import GenerationInputs, run_generation

router = APIRouter(prefix="/proposals", tags=["proposals"])

_RATE = get_settings().generate_rate_limit


def _inputs(body: ProposalCreate) -> GenerationInputs:
    return GenerationInputs(
        client_name=body.client_name,
        client_company=body.client_company,
        service_type=body.service_type.value,
        brief_text=body.brief_text,
        notes=body.notes,
        tone=body.tone.value,
        pricing_mode=body.pricing_mode.value,
        package_ids=body.package_ids,
        hourly=[o.model_dump() for o in body.hourly] if body.hourly else None,
        fixed=body.fixed.model_dump() if body.fixed else None,
    )


@router.post("", response_model=ProposalView, status_code=status.HTTP_201_CREATED)
@limiter.limit(_RATE, key_func=generate_rate_key)
async def create_proposal(
    request: Request,
    body: ProposalCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProposalView:
    try:
        proposal = await run_generation(db, user, _inputs(body))
    except AIGenerationError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"generation failed: {exc}") from exc
    return ProposalView.from_model(proposal)


@router.get("", response_model=list[ProposalView])
async def list_proposals(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[ProposalView]:
    rows = (
        await db.execute(
            select(Proposal).where(Proposal.user_id == user.id).order_by(Proposal.created_at.desc())
        )
    ).scalars()
    return [ProposalView.from_model(p) for p in rows]


@router.get("/{proposal_id}", response_model=ProposalView)
async def get_proposal(proposal: Proposal = Depends(get_owned_proposal)) -> ProposalView:
    return ProposalView.from_model(proposal)


@router.patch("/{proposal_id}", response_model=ProposalView)
async def patch_proposal(
    body: ProposalPatch,
    proposal: Proposal = Depends(get_owned_proposal),
    db: AsyncSession = Depends(get_db),
) -> ProposalView:
    data = body.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "empty patch")

    if "client_name" in data:
        proposal.client_name = data["client_name"]
    if "client_company" in data:
        proposal.client_company = data["client_company"]
    if "status" in data:
        proposal.status = ProposalStatus(data["status"]).value

    pj = dict(proposal.proposal_json or {})
    if data.get("sections"):
        for key, value in data["sections"].items():
            if value is not None:
                pj[key] = value
    if data.get("pricing") is not None:
        lines = list(pj.get("pricing", []))
        for i, patch_line in enumerate(data["pricing"]):
            if i >= len(lines):
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"no pricing line {i}")
            if patch_line.get("label") is not None:
                lines[i]["label"] = patch_line["label"]
            if patch_line.get("amount_minor") is not None:
                lines[i]["amount_minor"] = patch_line["amount_minor"]
        pj["pricing"] = lines
    proposal.proposal_json = pj

    proposal.pdf_url = None  # invalidate cached PDF (mvp-spec.md §7)
    await db.flush()
    await db.refresh(proposal)
    return ProposalView.from_model(proposal)


@router.post("/{proposal_id}/regenerate", response_model=ProposalView)
@limiter.limit(_RATE, key_func=generate_rate_key)
async def regenerate_proposal(
    request: Request,
    proposal: Proposal = Depends(get_owned_proposal),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProposalView:
    pi = proposal.pricing_input or {}
    inputs = GenerationInputs(
        client_name=proposal.client_name,
        client_company=proposal.client_company,
        service_type=proposal.service_type,
        brief_text=proposal.brief_text,
        notes=proposal.notes,
        tone=proposal.tone,
        pricing_mode=proposal.pricing_mode,
        package_ids=[uuid.UUID(x) for x in (pi.get("package_ids") or [])] or None,
        hourly=pi.get("hourly"),
        fixed=pi.get("fixed"),
    )
    try:
        updated = await run_generation(db, user, inputs, existing=proposal)
    except AIGenerationError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"generation failed: {exc}") from exc
    return ProposalView.from_model(updated)


@router.post(
    "/{proposal_id}/duplicate", response_model=ProposalView, status_code=status.HTTP_201_CREATED
)
async def duplicate_proposal(
    proposal: Proposal = Depends(get_owned_proposal),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProposalView:
    # Clone inputs + last server JSON. No model call until the user regenerates
    # (mvp-spec.md §3.1). No quota.
    clone = Proposal(
        user_id=user.id,
        client_name=proposal.client_name,
        client_company=proposal.client_company,
        service_type=proposal.service_type,
        brief_text=proposal.brief_text,
        notes=proposal.notes,
        pricing_mode=proposal.pricing_mode,
        tone=proposal.tone,
        status=ProposalStatus.draft.value,
        pricing_input=dict(proposal.pricing_input or {}),
        proposal_json=dict(proposal.proposal_json or {}),
        pdf_url=None,
    )
    db.add(clone)
    await db.flush()
    await db.refresh(clone)
    return ProposalView.from_model(clone)


@router.get("/{proposal_id}/pdf")
async def get_pdf(proposal: Proposal = Depends(get_owned_proposal)) -> dict:
    # Wave 3 stub. Real server-side rendering + signed URL is Wave 4.
    # No LLM, no quota.
    raise HTTPException(
        status.HTTP_501_NOT_IMPLEMENTED,
        detail={"error": "pdf_not_implemented", "hint": "Server-side PDF rendering lands in Wave 4."},
    )
