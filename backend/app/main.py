"""FastAPI app. All routers mount under /v1. Business logic lives in services/."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import get_settings
from app.core.rate_limit import limiter
from app.routers import billing, health, me, proposals
from app.services.ai import validate_startup_config as validate_ai
from app.services.email import validate_startup_config as validate_email
from app.services.payments import validate_startup_config as validate_payments
from app.services.storage import validate_startup_config as validate_storage

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Schema is owned by Alembic (`alembic upgrade head` runs before this boots).
    Path(settings.storage_local_path).mkdir(parents=True, exist_ok=True)
    # Fail fast on a misconfigured adapter rather than on the first request.
    validate_ai()
    validate_payments()
    validate_storage()
    validate_email()
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Single-operator AI proposal / quote generator — v0 platform skeleton",
    lifespan=lifespan,
    debug=settings.debug,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

V1 = "/v1"
app.include_router(health.router, prefix=V1)
app.include_router(me.router, prefix=V1)
app.include_router(proposals.router, prefix=V1)
app.include_router(billing.router, prefix=V1)


@app.get("/")
async def root() -> dict:
    return {"app": settings.app_name, "docs": "/docs", "health": "/v1/health"}
