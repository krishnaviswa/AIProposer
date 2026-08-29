"""S-004 — live Razorpay provider (Orders API stubbed) + HMAC webhook."""

from __future__ import annotations

import json
import types
import uuid

import pytest

from app.config import get_settings
from app.services.payments.hmac_util import sign_body
from app.services.payments.razorpay import RazorpayPaymentProvider

SECRET = "rzp-webhook-secret"


@pytest.fixture(autouse=True)
def _razorpay_keys(monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "razorpay_key_id", "rzp_test_abc")
    monkeypatch.setattr(s, "razorpay_key_secret", "secret_xyz")
    monkeypatch.setattr(s, "razorpay_webhook_secret", SECRET)
    yield


def _razorpay_event(user_id: str, *, event: str = "order.paid", plan_id: str = "starter_inr") -> dict:
    return {
        "id": "evt_rzp_1",
        "event": event,
        "payload": {
            "order": {
                "entity": {
                    "id": "order_rzp_1",
                    "amount": 50000,
                    "receipt": f"user:{user_id}",
                    "notes": {"user_id": user_id, "plan_id": plan_id},
                }
            },
            "payment": {"entity": {"id": "pay_rzp_1", "order_id": "order_rzp_1"}},
        },
    }


def test_webhook_signature_and_note_extraction():
    p = RazorpayPaymentProvider()
    uid = str(uuid.uuid4())
    body = json.dumps(_razorpay_event(uid)).encode()
    ok = p.verify_webhook(body, sign_body(SECRET, body))
    assert ok is not None
    assert ok.paid is True
    assert ok.plan_id == "starter_inr"
    assert ok.notes["user_id"] == uid
    assert ok.provider_order_id == "order_rzp_1"

    assert p.verify_webhook(body, "bad-signature") is None


def test_webhook_non_paid_event_is_not_paid():
    p = RazorpayPaymentProvider()
    body = json.dumps(_razorpay_event(str(uuid.uuid4()), event="payment.failed")).encode()
    ev = p.verify_webhook(body, sign_body(SECRET, body))
    assert ev is not None and ev.paid is False


async def test_create_order_calls_orders_api(monkeypatch):
    captured = {}

    class _FakeResp:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return {"id": "order_rzp_new", "amount": 50000, "currency": "INR", "status": "created"}

    class _FakeClient:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, auth=None, json=None):
            captured.update(url=url, auth=auth, json=json)
            return _FakeResp()

    monkeypatch.setattr("app.services.payments.razorpay.httpx.AsyncClient", _FakeClient)

    order = await RazorpayPaymentProvider().create_order(
        amount_paise=50000, currency="INR", plan_id="starter_inr", receipt="user:x",
        notes={"user_id": "x"},
    )
    assert order.provider_order_id == "order_rzp_new"
    assert order.amount_paise == 50000
    assert captured["url"].endswith("/orders")
    assert captured["auth"] == ("rzp_test_abc", "secret_xyz")
    assert captured["json"]["amount"] == 50000
    assert captured["json"]["notes"]["plan_id"] == "starter_inr"


def test_startup_requires_keys(monkeypatch):
    from app.services.payments import validate_startup_config

    s = get_settings()
    monkeypatch.setattr(s, "payments_provider", "razorpay")
    monkeypatch.setattr(s, "razorpay_key_secret", "")
    with pytest.raises(RuntimeError, match="RAZORPAY"):
        validate_startup_config()


async def test_checkout_and_webhook_end_to_end_with_razorpay(client, auth, monkeypatch):
    """PAYMENTS_PROVIDER=razorpay: checkout hits the (stubbed) Orders API, then a
    signed Razorpay-shaped webhook upgrades the plan."""
    s = get_settings()
    monkeypatch.setattr(s, "payments_provider", "razorpay")

    class _FakeResp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"id": "order_rzp_e2e", "amount": 50000, "currency": "INR"}

    class _FakeClient:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, *a, **k):
            return _FakeResp()

    monkeypatch.setattr("app.services.payments.razorpay.httpx.AsyncClient", _FakeClient)

    co = await client.post(
        "/v1/billing/checkout-session", headers=auth["headers"], json={"plan_id": "starter_inr"}
    )
    assert co.status_code == 200, co.text
    assert co.json()["provider_order_id"] == "order_rzp_e2e"

    me = (await client.get("/v1/me", headers=auth["headers"])).json()
    assert me["plan"]["id"] == "free"  # not upgraded until the webhook

    body = json.dumps(_razorpay_event(auth["sub"])).encode()
    wh = await client.post(
        "/v1/billing/webhook", content=body, headers={"X-Signature": sign_body(SECRET, body)}
    )
    assert wh.status_code == 200 and wh.json()["applied"] is True

    me2 = (await client.get("/v1/me", headers=auth["headers"])).json()
    assert me2["plan"]["id"] == "starter_inr"
    assert me2["usage"]["included"] == 20
