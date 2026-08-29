"""AC 20 (rate limit) + AC 21 (no real AI wired; boot check fails for non-mock)."""

from __future__ import annotations

import pytest

from app.services.ai import REGISTERED_PROVIDERS, get_ai_provider, validate_startup_config
from app.services.ai.mock import MockAIProvider
from tests.helpers import set_packages


async def test_generate_is_rate_limited(client, auth):
    # Upgrade to Starter (20 quota) so the rate limit (10/min), not the quota,
    # is what trips first.
    import json

    from app.config import get_settings
    from app.services.payments.hmac_util import sign_body

    payload = {"id": "evt_rl", "event": "order.paid", "plan_id": "starter_inr",
               "receipt": f"user:{auth['sub']}"}
    body = json.dumps(payload).encode()
    await client.post(
        "/v1/billing/webhook",
        content=body,
        headers={"X-Signature": sign_body(get_settings().razorpay_webhook_secret, body)},
    )
    await set_packages(client, auth["headers"], [])

    statuses = []
    for i in range(13):
        r = await client.post(
            "/v1/proposals",
            headers=auth["headers"],
            json={
                "client_name": "Acme",
                "service_type": "other",
                "brief_text": f"tiny brief {i}",
                "tone": "formal",
                "pricing_mode": "fixed",
                "fixed": {"label": "P", "amount_minor": 1000},
            },
        )
        statuses.append(r.status_code)
    assert 429 in statuses, statuses
    assert statuses.count(201) <= 10  # limiter capped the successes


def test_only_mock_ai_is_registered():
    assert REGISTERED_PROVIDERS == ("mock",)
    assert isinstance(get_ai_provider(), MockAIProvider)


def test_non_mock_ai_provider_fails_startup(monkeypatch):
    from app.config import get_settings

    s = get_settings()
    monkeypatch.setattr(s, "ai_provider", "openai")
    with pytest.raises(RuntimeError) as exc:
        validate_startup_config()
    assert "Wave 4" in str(exc.value)
