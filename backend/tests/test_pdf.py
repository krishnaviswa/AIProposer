"""S-003 — server-side PDF render + cache + watermark + invalidation."""

from __future__ import annotations

from app.services.pdf import render_proposal_pdf
from tests.helpers import generate, set_packages

PJ = {
    "executive_summary": "A short plan.",
    "scope_of_work": ["Discovery", "Build"],
    "timeline": [{"label": "Week 1", "detail": "Kickoff"}],
    "pricing": [{"label": "Basic", "amount_minor": 500000, "currency": "INR", "justification": "core"}],
    "terms": ["50% upfront"],
    "followup_email": "Hi\nthere",
}


def test_render_returns_a_pdf():
    data = render_proposal_pdf(PJ, watermark=False, client_name="Acme")
    assert data[:5] == b"%PDF-"
    assert len(data) > 800


def test_watermark_changes_the_document():
    plain = render_proposal_pdf(PJ, watermark=False, client_name="Acme")
    marked = render_proposal_pdf(PJ, watermark=True, client_name="Acme")
    assert plain[:5] == b"%PDF-" and marked[:5] == b"%PDF-"
    assert plain != marked


async def test_pdf_endpoint_caches_and_reuses(client, auth, monkeypatch):
    await set_packages(client, auth["headers"], [])
    code, p = await generate(
        client, auth["headers"], pricing_mode="fixed", fixed={"label": "P", "amount_minor": 100000}
    )
    assert code == 201

    calls = {"n": 0}
    import app.routers.proposals as pr

    real = pr.render_proposal_pdf

    def counting(*a, **k):
        calls["n"] += 1
        return real(*a, **k)

    monkeypatch.setattr(pr, "render_proposal_pdf", counting)

    r1 = await client.get(f"/v1/proposals/{p['id']}/pdf", headers=auth["headers"])
    r2 = await client.get(f"/v1/proposals/{p['id']}/pdf", headers=auth["headers"])
    assert r1.status_code == 200 and r2.status_code == 200
    assert calls["n"] == 1  # cache hit on the second call — rendered once

    # PATCH nulls pdf_url -> re-render
    await client.patch(
        f"/v1/proposals/{p['id']}", headers=auth["headers"], json={"client_name": "New"}
    )
    r3 = await client.get(f"/v1/proposals/{p['id']}/pdf", headers=auth["headers"])
    assert r3.status_code == 200
    assert calls["n"] == 2

    me = (await client.get("/v1/me", headers=auth["headers"])).json()
    assert me["usage"]["used"] == 1  # PDF path never touches quota


async def test_pdf_is_owner_scoped(client, user_factory):
    _, a = user_factory("a@x.com")
    _, b = user_factory("b@x.com")
    await client.get("/v1/me", headers=a)
    await client.get("/v1/me", headers=b)
    await set_packages(client, a, [])
    code, p = await generate(
        client, a, pricing_mode="fixed", fixed={"label": "P", "amount_minor": 1000}
    )
    assert code == 201
    r = await client.get(f"/v1/proposals/{p['id']}/pdf", headers=b)
    assert r.status_code == 404
