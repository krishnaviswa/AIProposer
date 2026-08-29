"""S-005 — optional phone-OTP login (ADR-003).

The SMS send is Supabase Auth's job; FastAPI only verifies the resulting JWT.
These tests cover the `phone` claim path and the `AUTH_PHONE_OTP` feature flag.
"""

from __future__ import annotations

import uuid

import pytest

from app.config import Settings, get_settings
from tests.conftest import make_token


@pytest.fixture
def phone_otp_on(monkeypatch):
    monkeypatch.setattr(get_settings(), "auth_phone_otp", True)


def test_auth_phone_otp_flag_binds_to_env_var(monkeypatch):
    """The documented switch is AUTH_PHONE_OTP (field name == env name). Regression
    guard: an earlier field name `auth_phone_otp_enabled` bound to AUTH_PHONE_OTP_ENABLED,
    so setting AUTH_PHONE_OTP (as .env.example / docker-compose.yml do) did nothing."""
    monkeypatch.setenv("AUTH_PHONE_OTP", "true")
    assert Settings(_env_file=None).auth_phone_otp is True
    monkeypatch.setenv("AUTH_PHONE_OTP", "false")
    assert Settings(_env_file=None).auth_phone_otp is False


async def test_phone_only_token_rejected_when_flag_off(client):
    tok = make_token(phone="+919000000001")
    r = await client.get("/v1/me", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 401


async def test_phone_only_token_provisions_account_when_flag_on(client, phone_otp_on):
    sub = str(uuid.uuid4())
    tok = make_token(sub, phone="+919000000002")
    r = await client.get("/v1/me", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["id"] == sub
    assert body["phone"] == "+919000000002"
    assert body["email"] is None
    assert body["plan"]["id"] == "free"


async def test_email_login_still_works_and_reports_no_phone(client):
    sub = str(uuid.uuid4())
    tok = make_token(sub, email="e@example.com")
    body = (await client.get("/v1/me", headers={"Authorization": f"Bearer {tok}"})).json()
    assert body["email"] == "e@example.com"
    assert body["phone"] is None


async def test_phone_backfilled_onto_existing_email_account(client, phone_otp_on):
    sub = str(uuid.uuid4())
    await client.get(
        "/v1/me", headers={"Authorization": f"Bearer {make_token(sub, email='p@example.com')}"}
    )
    linked = make_token(sub, email="p@example.com", phone="+919000000003")
    body = (await client.get("/v1/me", headers={"Authorization": f"Bearer {linked}"})).json()
    assert body["email"] == "p@example.com"
    assert body["phone"] == "+919000000003"


async def test_phone_claim_backfilled_onto_email_account_even_when_flag_off(client):
    """A token carrying BOTH email and phone is a valid account (it has an email),
    so its Supabase-verified phone is recorded regardless of AUTH_PHONE_OTP. The flag
    only gates phone-*only* identities. This is intentional — see deps.get_current_user."""
    sub = str(uuid.uuid4())
    await client.get(
        "/v1/me", headers={"Authorization": f"Bearer {make_token(sub, email='both@example.com')}"}
    )
    linked = make_token(sub, email="both@example.com", phone="+919000000009")
    body = (await client.get("/v1/me", headers={"Authorization": f"Bearer {linked}"})).json()
    assert body["email"] == "both@example.com"
    assert body["phone"] == "+919000000009"


async def test_token_with_neither_email_nor_phone_is_401(client):
    import datetime as dt

    import jwt

    s = get_settings()
    tok = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "aud": s.supabase_jwt_aud,
            "exp": dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=1),
        },
        s.supabase_jwt_secret,
        algorithm="HS256",
    )
    r = await client.get("/v1/me", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 401
