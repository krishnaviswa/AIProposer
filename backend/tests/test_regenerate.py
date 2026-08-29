"""AC 14 — regenerate re-derives prices from the user's CURRENT saved amounts,
nulls the PDF, and burns quota; a failure keeps the old copy and the counter."""

from __future__ import annotations

from tests.helpers import generate, set_packages


async def test_regenerate_tracks_current_saved_package_amount(client, auth):
    me = await set_packages(client, auth["headers"], [{"label": "Basic", "amount_minor": 500000}])
    ids = [p["id"] for p in me["packages"]]
    code, first = await generate(client, auth["headers"], package_ids=ids)
    assert code == 201 and first["pricing"][0]["amount_minor"] == 500000

    # Editing the price keeps the package id stable (label-keyed upsert).
    me2 = await set_packages(client, auth["headers"], [{"label": "Basic", "amount_minor": 900000}])
    assert [p["id"] for p in me2["packages"]] == ids

    r = await client.post(f"/v1/proposals/{first['id']}/regenerate", headers=auth["headers"])
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["pricing"][0]["amount_minor"] == 900000  # re-derived, not frozen
    assert body["pdf_url"] is None

    me3 = (await client.get("/v1/me", headers=auth["headers"])).json()
    assert me3["usage"]["used"] == 2


async def test_regenerate_over_quota_is_402(client, auth):
    await set_packages(client, auth["headers"], [])
    code, first = await generate(
        client, auth["headers"], pricing_mode="fixed", fixed={"label": "P", "amount_minor": 1000}
    )
    assert code == 201
    # burn the rest of the free quota
    for _ in range(2):
        c, _b = await generate(
            client, auth["headers"], pricing_mode="fixed", fixed={"label": "P", "amount_minor": 1000}
        )
        assert c == 201
    r = await client.post(f"/v1/proposals/{first['id']}/regenerate", headers=auth["headers"])
    assert r.status_code == 402


async def test_regenerate_failure_keeps_old_copy_and_quota(client, auth):
    await set_packages(client, auth["headers"], [])
    code, first = await generate(
        client, auth["headers"], pricing_mode="fixed", fixed={"label": "P", "amount_minor": 5000}
    )
    assert code == 201
    original = first["sections"]["executive_summary"]

    code2, _ = await generate(
        client,
        auth["headers"],
        pricing_mode="fixed",
        fixed={"label": "P", "amount_minor": 5000},
        brief="ship it __FAIL__ tomorrow",
    )
    assert code2 == 502

    detail = (await client.get(f"/v1/proposals/{first['id']}", headers=auth["headers"])).json()
    assert detail["sections"]["executive_summary"] == original  # untouched

    me = (await client.get("/v1/me", headers=auth["headers"])).json()
    assert me["usage"]["used"] == 1
