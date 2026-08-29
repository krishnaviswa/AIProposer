"""AC 6, 7, 8, 9, 10 — generate with the mock model."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.models import Proposal, UsageRecord
from tests.helpers import generate, set_packages


async def test_generate_uses_server_prices_and_returns_dto(client, auth, db_engine):
    me = await set_packages(
        client,
        auth["headers"],
        [{"label": "Basic", "amount_minor": 500000}, {"label": "Pro", "amount_minor": 1200000}],
    )
    ids = [p["id"] for p in me["packages"]]

    code, body = await generate(client, auth["headers"], package_ids=ids)
    assert code == 201, body

    assert body["pdf_url"] is None
    assert body["pricing"] == [
        {"label": "Basic", "amount_minor": 500000, "currency": "INR", "justification": body["pricing"][0]["justification"]},
        {"label": "Pro", "amount_minor": 1200000, "currency": "INR", "justification": body["pricing"][1]["justification"]},
    ]
    assert body["sections"]["executive_summary"]
    assert "proposal_json" not in body  # DTO only

    me2 = (await client.get("/v1/me", headers=auth["headers"])).json()
    assert me2["usage"]["used"] == 1


async def test_model_supplied_price_is_discarded(client, auth):
    me = await set_packages(client, auth["headers"], [{"label": "Only", "amount_minor": 777000}])
    ids = [p["id"] for p in me["packages"]]
    code, body = await generate(
        client, auth["headers"], package_ids=ids, brief="Website work __MODEL_TRIES_PRICE__ please"
    )
    assert code == 201
    assert [line["amount_minor"] for line in body["pricing"]] == [777000]


async def test_generation_failure_is_502_with_no_quota_and_no_row(client, auth, db_engine):
    me = await set_packages(client, auth["headers"], [{"label": "Basic", "amount_minor": 500000}])
    ids = [p["id"] for p in me["packages"]]

    code, body = await generate(client, auth["headers"], package_ids=ids, brief="do the thing __FAIL__")
    assert code == 502

    me2 = (await client.get("/v1/me", headers=auth["headers"])).json()
    assert me2["usage"]["used"] == 0

    from sqlalchemy.ext.asyncio import async_sessionmaker

    async with async_sessionmaker(db_engine)() as s:
        assert (await s.execute(select(Proposal))).scalars().first() is None


async def test_over_quota_is_402_no_model_call(client, auth):
    me = await set_packages(client, auth["headers"], [{"label": "Basic", "amount_minor": 500000}])
    ids = [p["id"] for p in me["packages"]]
    for _ in range(3):
        code, _ = await generate(client, auth["headers"], package_ids=ids)
        assert code == 201
    code, body = await generate(client, auth["headers"], package_ids=ids)
    assert code == 402
    assert body["detail"]["error"] == "quota_exhausted"

    me2 = (await client.get("/v1/me", headers=auth["headers"])).json()
    assert me2["usage"]["used"] == 3


async def test_hourly_mode_amount_is_rate_times_hours(client, auth):
    await set_packages(client, auth["headers"], [], hourly_rate_minor=500000)
    code, body = await generate(
        client,
        auth["headers"],
        pricing_mode="hourly",
        hourly=[{"label": "Basic", "hours": 10}],
    )
    assert code == 201, body
    assert body["pricing"] == [
        {"label": "Basic", "amount_minor": 5000000, "currency": "INR", "justification": body["pricing"][0]["justification"]}
    ]


async def test_hourly_mode_without_saved_rate_is_422(client, auth):
    await set_packages(client, auth["headers"], [])
    code, body = await generate(
        client, auth["headers"], pricing_mode="hourly", hourly=[{"label": "Basic", "hours": 5}]
    )
    assert code == 422


async def test_fixed_mode_uses_user_typed_amount(client, auth):
    await set_packages(client, auth["headers"], [])
    code, body = await generate(
        client, auth["headers"], pricing_mode="fixed", fixed={"label": "Project", "amount_minor": 3400000}
    )
    assert code == 201, body
    assert body["pricing"][0]["amount_minor"] == 3400000


@pytest.mark.parametrize("bad_brief", ["", "x" * 1501])
async def test_brief_char_caps_enforced(client, auth, bad_brief):
    await set_packages(client, auth["headers"], [])
    r = await client.post(
        "/v1/proposals",
        headers=auth["headers"],
        json={
            "client_name": "Acme",
            "service_type": "design",
            "brief_text": bad_brief,
            "tone": "friendly",
            "pricing_mode": "fixed",
            "fixed": {"label": "P", "amount_minor": 1000},
        },
    )
    assert r.status_code == 422
