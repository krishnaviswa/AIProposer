"""AC 1-3, 21 (auth) + ADR-001 verifier unit tests."""

from __future__ import annotations

import uuid
from datetime import timedelta

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from app.auth import verify_jwt
from tests.conftest import make_token

PROTECTED = ["/v1/me", "/v1/proposals"]


@pytest.mark.parametrize("path", PROTECTED)
async def test_no_token_is_401(client, path):
    assert (await client.get(path)).status_code == 401


@pytest.mark.parametrize("path", PROTECTED)
async def test_garbage_token_is_401(client, path):
    r = await client.get(path, headers={"Authorization": "Bearer not-a-jwt"})
    assert r.status_code == 401


async def test_expired_token_is_401(client):
    tok = make_token(exp_delta=timedelta(hours=-1))
    assert (await client.get("/v1/me", headers={"Authorization": f"Bearer {tok}"})).status_code == 401


async def test_wrong_audience_is_401(client):
    tok = make_token(aud="some-other-service")
    assert (await client.get("/v1/me", headers={"Authorization": f"Bearer {tok}"})).status_code == 401


async def test_wrong_signature_is_401(client):
    tok = make_token(secret="not-the-real-secret")
    assert (await client.get("/v1/me", headers={"Authorization": f"Bearer {tok}"})).status_code == 401


async def test_valid_token_provisions_user_with_free_plan(client):
    sub = str(uuid.uuid4())
    tok = make_token(sub, email="new@example.com")
    r = await client.get("/v1/me", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == sub
    assert body["email"] == "new@example.com"
    assert body["plan"]["id"] == "free"
    assert body["plan"]["proposals_included"] == 3
    assert body["usage"]["used"] == 0


# --- ADR-001: verifier itself -------------------------------------------------


def test_verify_hs256_roundtrip():
    tok = make_token(sub="11111111-1111-1111-1111-111111111111")
    claims = verify_jwt(tok)
    assert claims["sub"] == "11111111-1111-1111-1111-111111111111"


def test_verify_rejects_missing_sub():
    import datetime as dt

    from app.config import get_settings

    s = get_settings()
    tok = jwt.encode(
        {"aud": s.supabase_jwt_aud, "exp": dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=1)},
        s.supabase_jwt_secret,
        algorithm="HS256",
    )
    with pytest.raises(jwt.InvalidTokenError):
        verify_jwt(tok)


def test_verify_rs256_with_local_keypair(monkeypatch):
    """The RS256 path, exercised against a locally generated key served as JWKS."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    class _FakeSigningKey:
        def __init__(self, k):
            self.key = k

    class _FakeJWKClient:
        def __init__(self, *a, **k):
            pass

        def get_signing_key_from_jwt(self, token):
            return _FakeSigningKey(key.public_key())

    import app.auth as auth_mod

    monkeypatch.setattr(auth_mod, "_get_jwks_client", lambda *a, **k: _FakeJWKClient())
    from app.config import get_settings

    s = get_settings()
    monkeypatch.setattr(s, "supabase_jwt_alg", "RS256")
    monkeypatch.setattr(s, "supabase_jwks_url", "https://example.test/jwks.json")

    tok = make_token(sub="22222222-2222-2222-2222-222222222222", alg="RS256", key=key)
    claims = verify_jwt(tok)
    assert claims["sub"] == "22222222-2222-2222-2222-222222222222"
