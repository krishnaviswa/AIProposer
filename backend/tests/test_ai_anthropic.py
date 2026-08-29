"""S-003 — the live Claude adapter, exercised with the SDK call stubbed.
No ANTHROPIC_API_KEY, no network."""

from __future__ import annotations

import types

import anthropic
import pytest

from app.services.ai.anthropic_provider import (
    AnthropicProvider,
    _PricingJustification,
    _ProposalCopySchema,
)
from app.services.ai.base import AIGenerationError, ProposalPromptInput
from app.services.ai.prompts import SYSTEM_PROMPT, build_user_payload

PAYLOAD = ProposalPromptInput(
    service_type="web_dev",
    tone="formal",
    client_name="Acme Co",
    client_company=None,
    brief_text="Build a 5-page marketing site.",
    notes=None,
    package_labels=["Basic", "Pro"],
)


def _fake_parsed() -> _ProposalCopySchema:
    return _ProposalCopySchema(
        executive_summary="A plan for Acme.",
        scope_of_work=["Discovery", "Build"],
        timeline=[{"label": "Week 1", "detail": "Kickoff"}],
        pricing=[
            {"label": "Basic", "justification": "covers the core build"},
            {"label": "Pro", "justification": "adds a CMS"},
        ],
        terms=["50% upfront"],
        followup_email="Hi Acme, following up.",
    )


def _fake_usage(**kw):
    base = dict(input_tokens=900, output_tokens=400, cache_read_input_tokens=0,
               cache_creation_input_tokens=0)
    base.update(kw)
    return types.SimpleNamespace(**base)


def _provider(monkeypatch, parse_impl):
    from app.config import get_settings

    s = get_settings()
    monkeypatch.setattr(s, "anthropic_api_key", "test-key")
    monkeypatch.setattr(s, "ai_model", "claude-haiku-4-5")
    p = AnthropicProvider()
    monkeypatch.setattr(p._client.messages, "parse", parse_impl)
    return p


def test_schema_has_no_money_field():
    # Structural guarantee: the model cannot return an amount.
    assert set(_PricingJustification.model_fields) == {"label", "justification"}
    schema_text = str(_ProposalCopySchema.model_json_schema()).lower()
    for bad in ("amount", "amount_minor", "price", "currency"):
        assert bad not in schema_text


def test_system_prompt_is_stable_and_injection_aware():
    assert "must NOT invent" in SYSTEM_PROMPT or "must NOT" in SYSTEM_PROMPT
    assert "untrusted" in SYSTEM_PROMPT.lower()
    # no volatile content that would break the cache prefix
    assert "202" not in SYSTEM_PROMPT and "{" not in SYSTEM_PROMPT


def test_user_payload_carries_labels_not_amounts():
    labelled = ProposalPromptInput(**{**PAYLOAD.__dict__, "package_labels": ["Basic", "Pro"]})
    text = build_user_payload(labelled)
    assert "Basic" in text and "Pro" in text
    # no amount VALUE or currency symbol — the assembler's numbers never reach the model
    for token in ("500000", "5000.00", "₹", "$", "€", "£"):
        assert token not in text


async def test_happy_path_maps_response_and_records_usage(monkeypatch):
    captured = {}

    async def fake_parse(**kwargs):
        captured.update(kwargs)
        return types.SimpleNamespace(
            parsed_output=_fake_parsed(), usage=_fake_usage(), stop_reason="end_turn"
        )

    provider = _provider(monkeypatch, fake_parse)
    result = await provider.generate_proposal_copy(PAYLOAD)

    assert result.executive_summary == "A plan for Acme."
    assert result.pricing_justifications == {
        "Basic": "covers the core build",
        "Pro": "adds a CMS",
    }
    assert result.usage.prompt_tokens == 900 and result.usage.completion_tokens == 400
    assert result.estimated_cost_usd > 0

    # request shape
    assert captured["model"] == "claude-haiku-4-5"
    assert captured["max_tokens"] == 2000
    assert captured["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert captured["output_format"] is _ProposalCopySchema
    assert "stream" not in captured  # mvp-spec.md §4: no streaming


@pytest.mark.parametrize("stop", ["refusal", "max_tokens"])
async def test_refusal_or_truncation_becomes_generation_error(monkeypatch, stop):
    async def fake_parse(**kwargs):
        return types.SimpleNamespace(parsed_output=None, usage=_fake_usage(), stop_reason=stop)

    provider = _provider(monkeypatch, fake_parse)
    with pytest.raises(AIGenerationError):
        await provider.generate_proposal_copy(PAYLOAD)


async def test_sdk_error_becomes_generation_error(monkeypatch):
    async def fake_parse(**kwargs):
        raise anthropic.APIError("boom", request=None, body=None)

    provider = _provider(monkeypatch, fake_parse)
    with pytest.raises(AIGenerationError):
        await provider.generate_proposal_copy(PAYLOAD)


def test_missing_key_raises_at_construction(monkeypatch):
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "anthropic_api_key", "")
    with pytest.raises(AIGenerationError):
        AnthropicProvider()


async def test_generate_end_to_end_with_stubbed_anthropic(client, auth, monkeypatch):
    """AI_PROVIDER=anthropic through POST /v1/proposals — money still comes from
    the user, not the model."""

    async def fake_parse(**kwargs):
        return types.SimpleNamespace(
            parsed_output=_fake_parsed(), usage=_fake_usage(), stop_reason="end_turn"
        )

    def fake_get_provider():
        from app.config import get_settings

        monkeypatch.setattr(get_settings(), "anthropic_api_key", "test-key")
        p = AnthropicProvider()
        p._client.messages.parse = fake_parse
        return p

    monkeypatch.setattr("app.services.generation.get_ai_provider", fake_get_provider)

    from tests.helpers import set_packages

    me = await set_packages(
        client, auth["headers"], [{"label": "Basic", "amount_minor": 500000}, {"label": "Pro", "amount_minor": 1200000}]
    )
    ids = [p["id"] for p in me["packages"]]
    r = await client.post(
        "/v1/proposals",
        headers=auth["headers"],
        json={
            "client_name": "Acme Co",
            "service_type": "web_dev",
            "brief_text": "Build a 5-page marketing site.",
            "tone": "formal",
            "pricing_mode": "packages",
            "package_ids": ids,
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert [(l["label"], l["amount_minor"]) for l in body["pricing"]] == [
        ("Basic", 500000),
        ("Pro", 1200000),
    ]
    assert body["pricing"][0]["justification"] == "covers the core build"
    assert body["sections"]["executive_summary"] == "A plan for Acme."
