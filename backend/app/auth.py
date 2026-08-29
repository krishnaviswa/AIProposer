"""Supabase JWT verification (ADR-001).

FastAPI only *verifies* the token — it never issues one. HS256 (shared secret)
is the dev/test default and needs no network; RS256 fetches Supabase's JWKS and
caches the key set. Every failure path raises InvalidTokenError → the caller
turns it into a 401 (fail closed, never 500).
"""

from __future__ import annotations

import time

import jwt
from jwt import InvalidTokenError, PyJWKClient

from app.config import get_settings

_jwks_client: PyJWKClient | None = None
_jwks_client_made_at: float = 0.0


def _get_jwks_client(url: str, ttl: int) -> PyJWKClient:
    global _jwks_client, _jwks_client_made_at
    now = time.monotonic()
    if _jwks_client is None or (now - _jwks_client_made_at) > ttl:
        _jwks_client = PyJWKClient(url, cache_keys=True, lifespan=ttl)
        _jwks_client_made_at = now
    return _jwks_client


def reset_jwks_cache() -> None:
    """Test hook — drop the cached JWKS client."""
    global _jwks_client, _jwks_client_made_at
    _jwks_client = None
    _jwks_client_made_at = 0.0


def verify_jwt(token: str) -> dict:
    """Return the validated claims dict, or raise jwt.InvalidTokenError."""
    settings = get_settings()
    options = {"require": ["exp", "sub"]}

    if settings.supabase_jwt_alg == "RS256":
        if not settings.supabase_jwks_url:
            raise InvalidTokenError("SUPABASE_JWKS_URL is not configured")
        try:
            signing_key = _get_jwks_client(
                settings.supabase_jwks_url, settings.supabase_jwks_cache_seconds
            ).get_signing_key_from_jwt(token)
        except Exception as exc:  # network / key-not-found — fail closed
            raise InvalidTokenError(f"JWKS lookup failed: {exc}") from exc
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=settings.supabase_jwt_aud,
            options=options,
        )

    return jwt.decode(
        token,
        settings.supabase_jwt_secret,
        algorithms=["HS256"],
        audience=settings.supabase_jwt_aud,
        options=options,
    )
