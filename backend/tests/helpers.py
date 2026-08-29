"""Shared test helpers built on the fixtures in conftest.py."""

from __future__ import annotations

from httpx import AsyncClient

_BRIEF = "Build a marketing website for a boutique consultancy. Five pages, CMS, contact form."


async def set_packages(client: AsyncClient, headers: dict, packages: list[dict], **profile) -> dict:
    body = {"quote_currency": profile.get("quote_currency", "INR"), "packages": packages}
    if "hourly_rate_minor" in profile:
        body["hourly_rate_minor"] = profile["hourly_rate_minor"]
    r = await client.put("/v1/me", headers=headers, json=body)
    assert r.status_code == 200, r.text
    return r.json()


async def generate(
    client: AsyncClient,
    headers: dict,
    *,
    pricing_mode: str = "packages",
    package_ids: list[str] | None = None,
    hourly: list[dict] | None = None,
    fixed: dict | None = None,
    brief: str = _BRIEF,
) -> tuple[int, dict]:
    payload = {
        "client_name": "Acme Co",
        "service_type": "web_dev",
        "brief_text": brief,
        "tone": "formal",
        "pricing_mode": pricing_mode,
    }
    if package_ids is not None:
        payload["package_ids"] = package_ids
    if hourly is not None:
        payload["hourly"] = hourly
    if fixed is not None:
        payload["fixed"] = fixed
    r = await client.post("/v1/proposals", headers=headers, json=payload)
    return r.status_code, (r.json() if r.content else {})
