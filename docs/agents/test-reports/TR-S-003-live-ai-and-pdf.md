# TR-S-003: Live Claude adapter + cached PDF — Test report

| Field | Value |
|---|---|
| **Slice** | S-003 |
| **Author** | Tester |
| **Date** | 2026-08-29 |
| **Recommendation** | **Ship** |

---

## Summary

**56 backend pytest tests pass** (was 42; +14 for S-003, 3 S-001 tests rewritten for the new
behaviour). All 12 acceptance criteria are green. The live Claude adapter is exercised end to end
with the SDK call stubbed — no `ANTHROPIC_API_KEY`, no network. The response schema has **no money
field**, so the "model can't set prices" guarantee is now structural, not a filter. Refusal,
truncation, and SDK errors all become `AIGenerationError` → `502` / 0 quota. The PDF renders from
`proposal_json` with real `reportlab` (offline), caches on `pdf_url`, re-renders after PATCH,
watermarks Free, and is owner-scoped — with **no LLM call and no quota** anywhere on that path.
`docs/ai-touchpoints.md` and `mvp-spec.md` are byte-identical (verified `git diff --stat` empty).

---

## AC coverage matrix

| AC# | Description | Type | Test reference | Result |
|---|---|---|---|---|
| 1 | `anthropic` without key fails boot; `mock` needs nothing | A | `test_rate_limit_and_startup.py::test_anthropic_provider_requires_api_key`, `::test_mock_is_the_default_ai_provider` | Pass |
| 2 | `parse` call: no-money schema, `max_tokens=2000`, model from settings, cached system, no stream | A | `test_ai_anthropic.py::test_happy_path_maps_response_and_records_usage`, `::test_schema_has_no_money_field` | Pass |
| 3 | Maps prose + label-keyed justifications; records `TokenUsage` + `estimated_cost_usd` | A | `test_ai_anthropic.py::test_happy_path_maps_response_and_records_usage` | Pass |
| 4 | refusal / max_tokens / None / SDK error → `AIGenerationError` (→ 502, 0 quota) | A | `test_ai_anthropic.py::test_refusal_or_truncation_becomes_generation_error` (×2), `::test_sdk_error_becomes_generation_error`; `test_proposals_generate.py::test_generation_failure_is_502_with_no_quota_and_no_row` | Pass |
| 5 | `AI_PROVIDER=anthropic` e2e — persisted amounts == user's, justifications from model | A | `test_ai_anthropic.py::test_generate_end_to_end_with_stubbed_anthropic` | Pass |
| 6 | System prompt stable + injection-aware; payload carries labels not amounts | A | `test_ai_anthropic.py::test_system_prompt_is_stable_and_injection_aware`, `::test_user_payload_carries_labels_not_amounts` | Pass |
| 7 | First `GET .../pdf` renders + stores + sets `pdf_url`; no LLM, no quota | A | `test_pdf.py::test_pdf_endpoint_caches_and_reuses`, `test_proposals_crud.py::test_pdf_renders_and_is_cached` | Pass |
| 8 | Second `GET .../pdf` does not re-render (1 render total) | A | `test_pdf.py::test_pdf_endpoint_caches_and_reuses` (`calls["n"] == 1`) | Pass |
| 9 | PATCH nulls `pdf_url` → next hit re-renders | A | `test_pdf.py::test_pdf_endpoint_caches_and_reuses` (`calls["n"] == 2`), `test_proposals_crud.py::test_pdf_renders_and_is_cached` | Pass |
| 10 | Free → "NOT FOR SENDING" watermark + no follow-up; paid → clean | A | `test_pdf.py::test_watermark_changes_the_document`, `::test_render_returns_a_pdf` | Pass |
| 11 | Another user's proposal id → `404` | A | `test_pdf.py::test_pdf_is_owner_scoped` | Pass |
| 12 | `ai-touchpoints.md` + `mvp-spec.md` unchanged; sequences note + ADR-002 present | M | M-001 (`git diff --stat` empty), file review | Pass |

**Coverage:** 12 / 12 AC — 11 automated, 1 review.

---

## Backend tests

### Added / changed (14 net new)

- `tests/test_ai_anthropic.py` — 9 tests: schema-has-no-money, stable/injection-aware prompt,
  labels-not-amounts payload, happy-path mapping + request shape, refusal & max_tokens →
  `AIGenerationError` (parametrised), SDK error → `AIGenerationError`, missing-key at construction,
  e2e through `POST /v1/proposals` with stubbed SDK.
- `tests/test_pdf.py` — 5 tests: `%PDF-` header, watermark changes bytes, endpoint renders-once +
  reuse + PATCH-invalidation + 0-quota, owner-scoped `404`.
- `tests/test_rate_limit_and_startup.py` — rewrote `test_only_mock_ai_is_registered` →
  `test_mock_is_the_default_ai_provider`, `test_non_mock_ai_provider_fails_startup` →
  `test_unregistered_ai_provider_fails_startup` + new `test_anthropic_provider_requires_api_key`.
- `tests/test_proposals_crud.py` — `test_pdf_is_stubbed` → `test_pdf_renders_and_is_cached`.

### Run output

```
$ cd backend && PYTHONPATH=. python -m pytest -q
........................................................                 [100%]
56 passed in ~4s
```

---

## Frontend tests

None changed — S-003 is backend-only. The S-002 suite (8 Jest tests) is unaffected; the frontend
wiring for the real PDF + checkout is S-004.

---

## Manual / integration

| ID | Check | Result |
|---|---|---|
| M-001 | `git diff --stat docs/ai-touchpoints.md mvp-spec.md` empty | Pass |
| M-002 | Full suite green on `AI_PROVIDER=mock`; no network in any test | Pass |
| M-003 | `from app.main import app` + `lifespan(app)` on default config | Pass — "lifespan OK on default config" |

---

## Regressions

None. The 3 rewritten tests reflect *intended* behaviour change (AI turned on, PDF real). Wave 1
docs unchanged except the `architecture-sequences.md` build note (not a SYNC_GROUP file).

---

## Gaps / rework items (non-blocking)

1. **`LocalStorageProvider.signed_url` returns a path, not a signed short-TTL URL.** Fine for
   Compose; real signing needs an S3/Supabase storage adapter — roadmap.
2. **No live-model smoke test.** By design — CI has no key. A manual `AI_PROVIDER=anthropic` run
   against a real key is a pre-launch checklist item, not a CI gate.
3. **Prompt-cache hit rate unverified** — needs a real key + `usage.cache_read_input_tokens`
   inspection; folded into the roadmap "model bake-off".
4. **`reportlab` layout is functional, not designed** — a branded PDF template is later polish.

---

## Sign-off

- [x] All 12 AC mapped (11 automated, 1 review)
- [x] Money guarantee is structural (schema has no amount field) — asserted
- [x] Failure path still `502` + 0 quota + no row — asserted
- [x] PDF path has no LLM call and no quota — asserted
- [x] `docs/ai-touchpoints.md` unchanged — verified
- [x] Ready for PM acceptance
