"""Application settings. One source of truth; read via get_settings()."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "AIProposer"
    app_version: str = "0.1.0"
    # SQL echo + FastAPI traceback-in-response. Off unless an environment opts in.
    debug: bool = False

    # aiosqlite default keeps `docker compose` optional for a first run and lets
    # the test suite point at an in-memory DB. docker-compose.yml sets Postgres.
    database_url: str = "sqlite+aiosqlite:///./aiproposer.db"

    cors_origins: str = "http://localhost:3000"

    # --- Supabase Auth (FastAPI only VERIFIES the JWT; it never issues one) ---
    # ADR-001. HS256 (shared secret) is the dev/test default — no network.
    # RS256 (JWKS) is the documented path for real deploys.
    supabase_jwt_alg: Literal["HS256", "RS256"] = "HS256"
    supabase_jwt_secret: str = "dev-supabase-jwt-secret-change-me"
    supabase_jwks_url: str = ""
    supabase_jwt_aud: str = "authenticated"
    # JWKS key-set cache lifetime (RS256 path).
    supabase_jwks_cache_seconds: int = 600

    # --- Adapters: every one defaults to a no-network mock/local impl ---
    ai_provider: str = "mock"          # real providers land in Wave 4
    payments_provider: str = "mock"    # real Razorpay lands in Wave 4
    storage_provider: Literal["local"] = "local"
    email_provider: str = "mock"

    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    razorpay_webhook_secret: str = "dev-webhook-secret-change-me"

    storage_local_path: str = "./uploads"

    # Rate limit on POST /v1/proposals + regenerate (slowapi syntax).
    generate_rate_limit: str = "10/minute"

    # Free-plan usage window when there is no subscription anchor.
    free_period_days: int = 30

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
