"""AC 4, 5 — profile + packages."""

from __future__ import annotations


async def test_put_me_persists_profile_and_packages(client, auth):
    r = await client.put(
        "/v1/me",
        headers=auth["headers"],
        json={
            "name": "Priya",
            "quote_currency": "INR",
            "hourly_rate_minor": 250000,
            "packages": [
                {"label": "Basic", "amount_minor": 500000},
                {"label": "Pro", "amount_minor": 1200000},
            ],
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["name"] == "Priya"
    assert body["quote_currency"] == "INR"
    assert body["hourly_rate_minor"] == 250000
    assert [(p["label"], p["amount_minor"], p["currency"]) for p in body["packages"]] == [
        ("Basic", 500000, "INR"),
        ("Pro", 1200000, "INR"),
    ]
    assert body["usage"] == {
        "included": 3,
        "used": 0,
        "remaining": 3,
        "period_end": body["usage"]["period_end"],
    }

    again = (await client.get("/v1/me", headers=auth["headers"])).json()
    assert len(again["packages"]) == 2


async def test_put_me_rejects_bad_currency(client, auth):
    r = await client.put(
        "/v1/me",
        headers=auth["headers"],
        json={"quote_currency": "JPY", "packages": []},
    )
    assert r.status_code == 422


async def test_put_me_rejects_non_integer_amount(client, auth):
    r = await client.put(
        "/v1/me",
        headers=auth["headers"],
        json={"quote_currency": "USD", "packages": [{"label": "X", "amount_minor": 9.99}]},
    )
    assert r.status_code == 422


async def test_put_me_rejects_more_than_three_packages(client, auth):
    r = await client.put(
        "/v1/me",
        headers=auth["headers"],
        json={
            "quote_currency": "USD",
            "packages": [{"label": f"P{i}", "amount_minor": i * 1000} for i in range(4)],
        },
    )
    assert r.status_code == 422
