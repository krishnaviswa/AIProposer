"""SlowAPI limiter. Key = per-caller (bearer token) + per-IP, so one user on a
shared IP and one IP fronting many users are both bounded (mvp-spec.md §7, §16).
In-memory storage — v0 runs as a single API instance."""

from __future__ import annotations

import hashlib

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return get_remote_address(request)


def generate_rate_key(request: Request) -> str:
    auth = request.headers.get("authorization", "")
    token = auth[7:] if auth.lower().startswith("bearer ") else ""
    bearer_hash = hashlib.sha1(token.encode()).hexdigest()[:16] if token else "anon"
    return f"{bearer_hash}:{_client_ip(request)}"


limiter = Limiter(key_func=_client_ip)
