"""FastAPI dependencies: JWT → current user (provisioned on first sight),
and the ownership guard that is the entire RBAC surface in v0."""

from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import verify_jwt
from app.database import get_db
from app.models import Proposal, User

_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    try:
        claims = verify_jwt(credentials.credentials)
        user_id = uuid.UUID(str(claims["sub"]))
    except (InvalidTokenError, KeyError, ValueError) as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token") from exc

    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None:
        # First sight of this Supabase user — provision a local row (ADR-001).
        db.add(User(id=user_id, email=str(claims.get("email") or f"{user_id}@users.noreply")))
        await db.flush()
        user = (await db.execute(select(User).where(User.id == user_id))).scalar_one()
    if not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User is inactive")
    return user


async def get_owned_proposal(
    proposal_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Proposal:
    proposal = (
        await db.execute(select(Proposal).where(Proposal.id == proposal_id))
    ).scalar_one_or_none()
    # 404 (not 403) when it isn't yours — don't confirm the row exists.
    if proposal is None or proposal.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Proposal not found")
    return proposal
