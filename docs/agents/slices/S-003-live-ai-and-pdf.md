# Slice: S-003 — Live Claude adapter + server-side cached PDF

| Field | Value |
|---|---|
| **Slice ID** | S-003 |
| **Phase** | 2 AI + money |
| **Status** | Accepted |
| **Owner** | PM / 2026-08-29 |

> **Wave 4, first half.** Turns on the two documented v0 AI hops with a real Claude adapter, and
> replaces the PDF stub with a real server-side render. `mock` / stub stay the default and the only
> thing CI runs. **No LLM call is added to PATCH, PDF, login, or webhook** — if one appeared, the
> design would be rejected.

---

## User story

**As a** freelancer
**I want** Generate to produce real proposal copy and Download to give me a real PDF
**So that** the product does what it promises — a sendable artifact, not a mock

---

## Acceptance criteria

**Live LLM adapter (`AI_PROVIDER=anthropic`)**

1. **Given** `AI_PROVIDER=anthropic` with no `ANTHROPIC_API_KEY`, **when** the app boots, **then**
   `validate_startup_config` raises (fail fast). `AI_PROVIDER=mock` still needs nothing.
2. **Given** the adapter, **when** it calls Claude, **then** it uses `client.messages.parse` with
   `output_format` set to a schema that has **no amount / price / currency field**, `max_tokens`
   from settings (2000), the model from `AI_MODEL`, a cached system block, and **no streaming**.
3. **Given** the model returns copy, **when** it is mapped, **then** only `justification` (keyed by
   package label) and the prose fields are kept; `TokenUsage` and an `estimated_cost_usd` are recorded.
4. **Given** the model refuses (`stop_reason=refusal`), truncates (`stop_reason=max_tokens`), returns
   nothing parseable, or the SDK raises, **then** the adapter raises `AIGenerationError` →
   `POST /v1/proposals` returns `502`, `usage.used` unchanged, no row persisted (unchanged from S-001).
5. **Given** `AI_PROVIDER=anthropic` end to end (SDK stubbed), **when** a user with two saved
   packages generates, **then** the persisted `pricing` amounts equal the user's saved amounts and
   the justifications come from the model — money never originates in the model.
6. **Given** the system prompt, **when** inspected, **then** it contains no volatile content (no
   dates, no `{...}`), tells the model the amounts are fixed and must not be stated, and tells it to
   ignore instructions embedded in the brief (`mvp-spec.md` §16).

**Server-side cached PDF**

7. **Given** a generated proposal, **when** I `GET /v1/proposals/{id}/pdf` the first time, **then** a
   PDF is rendered from `proposal_json`, stored via the storage adapter, `pdf_url` is set, and the
   response is `{pdf_url}`. **No LLM call, no quota.**
8. **Given** `pdf_url` is already set, **when** I `GET .../pdf` again, **then** the PDF is **not**
   re-rendered (one render total) and a fresh URL is returned.
9. **Given** I `PATCH` the proposal, **then** `pdf_url` is nulled and the next `GET .../pdf`
   re-renders.
10. **Given** a Free-plan user, **when** the PDF renders, **then** it carries the "NOT FOR SENDING"
    watermark; a paid plan's PDF does not and includes the follow-up email.
11. **Given** another user's proposal id, **when** I `GET .../pdf`, **then** `404`.

**Docs**

12. **Given** the wave, **then** `docs/ai-touchpoints.md` is unchanged (two AI hops, same rules);
    `docs/architecture-sequences.md` build note updated; ADR-002 records the model choice;
    `mvp-spec.md` untouched.

---

## Out of scope

- Real Razorpay + frontend money/PDF wiring (S-004).
- Real signed storage URLs (S3 / Supabase Storage) — `LocalStorageProvider.signed_url` returns a
  path; real signing is roadmap.
- Prompt-cache verification / the ~20-brief model benchmark (roadmap: "model bake-off").
- Streaming, batch, vision, competitor-upload OCR.

---

## Dependencies

- `S-001` platform skeleton (Accepted), `S-002` client (Accepted).

---

## Definition of done (PM)

- [x] All 12 AC verified in the test report (56 backend tests, was 42)
- [x] `AI_PROVIDER=mock` and stub PDF still the CI default; no live keys in CI
- [x] `docs/ai-touchpoints.md` unchanged; `architecture-sequences.md` note updated; ADR-002 added
- [x] `mvp-spec.md` untouched; `docs/roadmap.md` unchanged (bake-off already listed)
- [x] `README.md` status updated
- [x] Parity check passes (no SYNC_GROUP file touched)
- [x] PM `Status: Accepted`

**PM acceptance (2026-08-29):** The money guarantee is now structural — the response schema has no
amount field, so there is nothing for the server to strip and no bug can ship model-invented prices
(AC 2, 5). Failure still costs 0 quota (AC 4). The PDF caches and invalidates correctly (AC 7–9) and
watermarks Free (AC 10) with no LLM anywhere near it. Model default meets the §4 cost target per
ADR-002. **Accepted.**

---

## Technical specification (Architect)

### Files

```
backend/app/services/ai/
  anthropic_provider.py   # AnthropicProvider + _ProposalCopySchema (no money field)
  prompts.py              # stable SYSTEM_PROMPT (§9.1) + build_user_payload (§9.2)
  __init__.py             # REGISTERED_PROVIDERS=("mock","anthropic"); key check
backend/app/services/pdf.py          # render_proposal_pdf(pj, *, watermark, client_name) -> bytes
backend/app/services/pricing.py      # + money() display helper (shared with the PDF)
backend/app/routers/proposals.py     # GET .../pdf: render-or-cache, watermark on Free
backend/app/config.py                # anthropic_api_key, ai_model, ai_max_tokens, ai_timeout_seconds
backend/requirements.txt             # + anthropic==1.2.0, reportlab==4.4.4
```

### Inference & money (cross-ref `docs/ai-touchpoints.md`)

- **LLM hops: exactly the two already documented** — `POST /v1/proposals`, `.../regenerate`, via
  `services/generation.run_generation` → `get_ai_provider().generate_proposal_copy`. Nowhere else.
- **PDF endpoint: no LLM, no quota.** Renders from the already-persisted `proposal_json`.
- **Money:** `_ProposalCopySchema.pricing` = `[{label, justification}]`. The final
  `proposal_json.pricing` is built in `generation.py` from `assembled.lines` (server `amount_minor` +
  `currency`) + `result.pricing_justifications[label]`. `ai-touchpoints.md` is accurate as written.

### Claude call (ADR-002)

`client.messages.parse(model=AI_MODEL, max_tokens=AI_MAX_TOKENS, system=[{text, cache_control:
ephemeral}], messages=[{user payload}], output_format=_ProposalCopySchema)`. `AsyncAnthropic(timeout,
max_retries=1)`. `stop_reason in {refusal, max_tokens}` or SDK error or `parsed_output is None` →
`AIGenerationError`.

### PDF

`reportlab` `BaseDocTemplate` (pure Python, no system libs — runs in CI). Watermark = an `onPage`
canvas hook drawing a rotated grey "NOT FOR SENDING" when `plan_id == "free"`; Free also omits the
follow-up email. Cache: `storage.put("proposals/{id}.pdf", bytes)` → `proposal.pdf_url = key`;
response is `storage.signed_url(key)`. `PATCH` already nulls `pdf_url`.

### Architect checklist

- [x] No `/v1` contract change beyond `GET .../pdf` now returning `{pdf_url}` instead of `501`
- [x] No new LLM call path; `docs/ai-touchpoints.md` still accurate
- [x] Money assembled server-side; schema structurally cannot carry an amount
- [x] `proposal_json` stays server-only; PDF is derived, not exposed as JSON
- [x] Adapters: `mock` + stub remain the CI default; real ones gated by env + key checks
- [x] No secrets committed — `.env.example` / compose use `${VAR:-}` placeholders

### Risks / tradeoffs

- **`LocalStorageProvider.signed_url` is not really signed** — returns `/uploads/<key>`. Fine for
  Compose; real signing (short-TTL, private bucket) is roadmap and belongs with an S3/Supabase adapter.
- **Haiku 4.5 copy quality** vs Sonnet/Opus — ADR-002; the benchmark decides the pin.
- **`reportlab` layout is plain** — a designed PDF template is later polish, not v0.

---

## Links

- Test plan: [`TP-S-003-live-ai-and-pdf.md`](../test-plans/TP-S-003-live-ai-and-pdf.md)
- Test report: [`TR-S-003-live-ai-and-pdf.md`](../test-reports/TR-S-003-live-ai-and-pdf.md)
- ADR: [`ADR-002-model-choice-and-structured-output.md`](../adrs/ADR-002-model-choice-and-structured-output.md)

---

## Changelog

| Date | Agent | Change |
|---|---|---|
| 2026-08-29 | PM | 12 AC — live adapter, structured-no-money, failure=0-quota, PDF cache/watermark |
| 2026-08-29 | Architect | ADR-002 (model, `parse()`, no-money schema); PDF render/cache design |
| 2026-08-29 | Builder | `anthropic_provider.py`, `prompts.py`, `pdf.py`, `money()`, PDF route; config + deps |
| 2026-08-29 | Tester | 56 backend tests (was 42); 12/12 AC; SDK + PDF fully stubbed/offline → Ship |
| 2026-08-29 | PM | Money guarantee is now structural; PDF has no LLM path → **Accepted** |
