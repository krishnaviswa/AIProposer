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

    # --- Adapters: default to a no-network mock/local impl; opt in per env ---
    ai_provider: str = "mock"          # "mock" | "anthropic"
    payments_provider: str = "mock"    # "mock" | "razorpay"
    storage_provider: Literal["local"] = "local"
    email_provider: str = "mock"

    # Claude LLM (ADR-002). Model is a mid-tier default per mvp-spec.md §4 —
    # the final pick comes from the §16 ~20-brief benchmark (roadmap: model bake-off).
    anthropic_api_key: str = ""
    ai_model: str = "claude-haiku-4-5"
    ai_max_tokens: int = 2000          # mvp-spec.md §4 output cap
    ai_timeout_seconds: float = 30.0

    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    razorpay_webhook_secret: str = "dev-webhook-secret-change-me"
    razorpay_api_base: str = "https://api.razorpay.com/v1"

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
