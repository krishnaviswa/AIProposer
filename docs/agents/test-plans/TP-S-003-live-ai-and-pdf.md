# TP-S-003: Live Claude adapter + cached PDF — Test plan

| Field | Value |
|---|---|
| **Slice** | S-003 |
| **Author** | Tester |
| **Date** | 2026-08-29 |

---

## Scope

The `AnthropicProvider` (with the SDK call stubbed) and the real `reportlab` PDF render + cache path.
No `ANTHROPIC_API_KEY`, no network, no live Razorpay. `AI_PROVIDER=mock` stays the default for every
other test in the suite.

---

## Test strategy

| Layer | Tool | Focus |
|---|---|---|
| Adapter | pytest + `monkeypatch` on `provider._client.messages.parse` | request shape, response mapping, refusal/truncation/SDK-error → `AIGenerationError`, structural no-money schema |
| Adapter (e2e) | pytest + stubbed `get_ai_provider` through `POST /v1/proposals` | `AI_PROVIDER=anthropic` path persists user amounts, model justifications |
| PDF | pytest — real `reportlab` (offline) | `%PDF-` header, watermark changes bytes, endpoint renders once + reuses, PATCH invalidates, owner-scoped, no quota |
| Startup | pytest | `anthropic` without key → boot fails; `mock` default unaffected |

Env: default settings (`AI_PROVIDER=mock`, no key). Adapter tests set `anthropic_api_key="test-key"`
via `monkeypatch` and replace `messages.parse`.

---

## AC → tests

| AC# | Test |
|---|---|
| 1 | `test_rate_limit_and_startup.py::test_anthropic_provider_requires_api_key`, `::test_mock_is_the_default_ai_provider` |
| 2 | `test_ai_anthropic.py::test_happy_path_maps_response_and_records_usage` (asserts `model`, `max_tokens=2000`, `cache_control`, `output_format`, no `stream`), `::test_schema_has_no_money_field` |
| 3 | `test_ai_anthropic.py::test_happy_path_maps_response_and_records_usage` (justifications keyed by label, usage + cost) |
| 4 | `test_ai_anthropic.py::test_refusal_or_truncation_becomes_generation_error` (parametrised), `::test_sdk_error_becomes_generation_error`; 0-quota path already covered by `test_proposals_generate.py::test_generation_failure_is_502_with_no_quota_and_no_row` |
| 5 | `test_ai_anthropic.py::test_generate_end_to_end_with_stubbed_anthropic` |
| 6 | `test_ai_anthropic.py::test_system_prompt_is_stable_and_injection_aware`, `::test_user_payload_carries_labels_not_amounts` |
| 7 | `test_pdf.py::test_pdf_endpoint_caches_and_reuses`; `test_proposals_crud.py::test_pdf_renders_and_is_cached` |
| 8 | `test_pdf.py::test_pdf_endpoint_caches_and_reuses` (render count == 1) |
| 9 | `test_pdf.py::test_pdf_endpoint_caches_and_reuses` (PATCH → render count == 2) |
| 10 | `test_pdf.py::test_watermark_changes_the_document`, `::test_render_returns_a_pdf` |
| 11 | `test_pdf.py::test_pdf_is_owner_scoped` |
| 12 | Manual — `docs/ai-touchpoints.md` diff empty; `architecture-sequences.md` note present; ADR-002 present; `mvp-spec.md` diff empty |

---

## Manual checklist

- [ ] M-001: `git diff docs/ai-touchpoints.md mvp-spec.md` is empty
- [ ] M-002: `AI_PROVIDER=mock` full suite (`pytest -q`) green; no test hits the network
- [ ] M-003: `python -c "from app.main import app"` + `lifespan(app)` OK on default config
