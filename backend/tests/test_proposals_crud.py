"""AC 11, 12, 13, 15, 16 — list / detail / PATCH allowlist / duplicate / pdf stub."""

from __future__ import annotations

from tests.helpers import generate, set_packages


async def _one_proposal(client, headers):
    me = await set_packages(client, headers, [{"label": "Basic", "amount_minor": 500000}])
    ids = [p["id"] for p in me["packages"]]
    code, body = await generate(client, headers, package_ids=ids)
    assert code == 201, body
    return body


async def test_list_and_detail_are_owner_scoped(client, user_factory):
    _, a_headers = user_factory("a@example.com")
    _, b_headers = user_factory("b@example.com")
    await client.get("/v1/me", headers=a_headers)
    await client.get("/v1/me", headers=b_headers)

    mine = await _one_proposal(client, a_headers)

    a_list = (await client.get("/v1/proposals", headers=a_headers)).json()
    b_list = (await client.get("/v1/proposals", headers=b_headers)).json()
    assert [p["id"] for p in a_list] == [mine["id"]]
    assert b_list == []

    assert (await client.get(f"/v1/proposals/{mine['id']}", headers=b_headers)).status_code == 404
    for p in a_list:
        assert "proposal_json" not in p


async def test_patch_allowlisted_field_updates_and_nulls_pdf(client, auth):
    p = await _one_proposal(client, auth["headers"])
    r = await client.patch(
        f"/v1/proposals/{p['id']}",
        headers=auth["headers"],
        json={
            "client_name": "Renamed Client",
            "status": "sent",
            "sections": {"executive_summary": "Hand-edited summary."},
            "pricing": [{"amount_minor": 654321}],
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["client_name"] == "Renamed Client"
    assert body["status"] == "sent"
    assert body["sections"]["executive_summary"] == "Hand-edited summary."
    assert body["pricing"][0]["amount_minor"] == 654321
    assert body["pdf_url"] is None

    me = (await client.get("/v1/me", headers=auth["headers"])).json()
    assert me["usage"]["used"] == 1  # PATCH did not burn quota


async def test_patch_unknown_key_is_422(client, auth):
    p = await _one_proposal(client, auth["headers"])
    for bad in ({"proposal_json": {}}, {"user_id": "x"}, {"llm_output_tokens": 5}, {"pdf_url": "hax"}):
        r = await client.patch(f"/v1/proposals/{p['id']}", headers=auth["headers"], json=bad)
        assert r.status_code == 422, (bad, r.text)


async def test_duplicate_clones_without_model_call_or_quota(client, auth):
    p = await _one_proposal(client, auth["headers"])
    r = await client.post(f"/v1/proposals/{p['id']}/duplicate", headers=auth["headers"])
    assert r.status_code == 201, r.text
    clone = r.json()
    assert clone["id"] != p["id"]
    assert clone["status"] == "draft"
    assert clone["sections"]["executive_summary"] == p["sections"]["executive_summary"]
    assert clone["pricing"] == p["pricing"]

    me = (await client.get("/v1/me", headers=auth["headers"])).json()
    assert me["usage"]["used"] == 1  # duplicate did not burn quota


async def test_pdf_is_stubbed(client, auth):
    p = await _one_proposal(client, auth["headers"])
    r = await client.get(f"/v1/proposals/{p['id']}/pdf", headers=auth["headers"])
    assert r.status_code == 501
    assert r.json()["detail"]["error"] == "pdf_not_implemented"

    me = (await client.get("/v1/me", headers=auth["headers"])).json()
    assert me["usage"]["used"] == 1
