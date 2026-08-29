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
from app.config import get_settings
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

    email = claims.get("email") or None
    phone = claims.get("phone") or None
    # Phone OTP is opt-in (ADR-003). With the flag off, a phone-only identity is
    # not a valid v0 account — reject it rather than silently provisioning one.
    if phone and not email and not get_settings().auth_phone_otp:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Phone sign-in is not enabled")
    if not email and not phone:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token has no email or phone")

    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None:
        # First sight of this Supabase user — provision a local row (ADR-001).
        db.add(User(id=user_id, email=email, phone=phone))
        await db.flush()
        user = (await db.execute(select(User).where(User.id == user_id))).scalar_one()
    elif user.phone is None and phone:
        # Backfill a Supabase-verified phone onto an existing account on a later
        # sign-in. Not gated by auth_phone_otp: the flag only blocks phone-*only*
        # identities; a row that already has an email is a valid v0 account.
        user.phone = phone
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
