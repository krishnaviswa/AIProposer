"""Test harness: an in-memory aiosqlite DB per test, the real app, real JWT
verification (HS256 dev secret). No network, no Postgres, no live vendors."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import get_settings
from app.database import Base, get_db
from app.main import app
from app.models import Plan
from app.services.ai.mock import MockAIProvider  # noqa: F401 (import parity)
from app.services.email.mock import MockEmailProvider
from app.services.payments.catalog import PLANS

SETTINGS = get_settings()


@pytest_asyncio.fixture
async def db_engine():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Seed the plan catalog.
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    async with sessionmaker() as s:
        for spec in PLANS.values():
            s.add(
                Plan(
                    id=spec["id"],
                    name=spec["name"],
                    rail=spec["rail"],
                    price_minor=spec["price_minor"],
                    proposals_included=spec["proposals_included"],
                    overage_minor=spec["overage_minor"],
                )
            )
        await s.commit()
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_engine):
    sessionmaker = async_sessionmaker(db_engine, expire_on_commit=False)

    async def _get_db():
        async with sessionmaker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = _get_db
    MockEmailProvider.sent.clear()
    from app.core.rate_limit import limiter

    limiter.reset()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


# --- auth helpers -----------------------------------------------------------


def make_token(
    sub: str | None = None,
    *,
    email: str | None = None,
    secret: str | None = None,
    aud: str | None = None,
    exp_delta: timedelta = timedelta(hours=1),
    alg: str = "HS256",
    key=None,
) -> str:
    sub = sub or str(uuid.uuid4())
    payload = {
        "sub": sub,
        "email": email or f"{sub}@example.com",
        "aud": aud or SETTINGS.supabase_jwt_aud,
        "exp": datetime.now(timezone.utc) + exp_delta,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, key or secret or SETTINGS.supabase_jwt_secret, algorithm=alg)


@pytest.fixture
def user_factory():
    """Returns (sub, headers) for a fresh user; the row is provisioned on first call."""

    def _make(email: str | None = None) -> tuple[str, dict]:
        sub = str(uuid.uuid4())
        token = make_token(sub, email=email)
        return sub, {"Authorization": f"Bearer {token}"}

    return _make


@pytest_asyncio.fixture
async def auth(client, user_factory):
    sub, headers = user_factory()
    # Touch /v1/me to provision the users row.
    await client.get("/v1/me", headers=headers)
    return {"sub": sub, "headers": headers}
