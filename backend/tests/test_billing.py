"""AC 17, 18, 19 — checkout stub + HMAC webhook + idempotency + plan/period anchor."""

from __future__ import annotations

import json

from app.config import get_settings
from app.services.payments.hmac_util import sign_body

SECRET = get_settings().razorpay_webhook_secret


def _signed(payload: dict) -> tuple[bytes, str]:
    body = json.dumps(payload).encode()
    return body, sign_body(SECRET, body)


async def test_checkout_session_returns_order_params_no_plan_change(client, auth):
    r = await client.post(
        "/v1/billing/checkout-session", headers=auth["headers"], json={"plan_id": "starter_inr"}
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["amount_paise"] == 50000
    assert body["currency"] == "INR"
    assert body["provider_order_id"].startswith("order_mock_")

    me = (await client.get("/v1/me", headers=auth["headers"])).json()
    assert me["plan"]["id"] == "free"  # unchanged until the webhook


async def test_checkout_rejects_unknown_or_free_plan(client, auth):
    assert (
        await client.post(
            "/v1/billing/checkout-session", headers=auth["headers"], json={"plan_id": "nope"}
        )
    ).status_code == 400
    assert (
        await client.post(
            "/v1/billing/checkout-session", headers=auth["headers"], json={"plan_id": "free"}
        )
    ).status_code == 400


async def test_webhook_upgrades_plan_and_is_idempotent(client, auth):
    payload = {
        "id": "evt_test_1",
        "event": "order.paid",
        "plan_id": "starter_inr",
        "receipt": f"user:{auth['sub']}",
    }
    body, sig = _signed(payload)

    r1 = await client.post("/v1/billing/webhook", content=body, headers={"X-Signature": sig})
    assert r1.status_code == 200 and r1.json()["applied"] is True

    me = (await client.get("/v1/me", headers=auth["headers"])).json()
    assert me["plan"]["id"] == "starter_inr"
    assert me["plan"]["proposals_included"] == 20
    assert me["usage"]["included"] == 20

    # Replay — same provider_event_id — must be a no-op.
    r2 = await client.post("/v1/billing/webhook", content=body, headers={"X-Signature": sig})
    assert r2.status_code == 200 and r2.json().get("duplicate") is True


async def test_webhook_bad_signature_is_400_no_change(client, auth):
    payload = {"id": "evt_bad", "event": "order.paid", "plan_id": "starter_inr",
               "receipt": f"user:{auth['sub']}"}
    body = json.dumps(payload).encode()
    r = await client.post("/v1/billing/webhook", content=body, headers={"X-Signature": "deadbeef"})
    assert r.status_code == 400

    me = (await client.get("/v1/me", headers=auth["headers"])).json()
    assert me["plan"]["id"] == "free"
