# AIProposer — AI touchpoints (v0)

**Status:** Wave 1 deliverable. Binding for Waves 2–4.
**Companion docs:** [`architecture.md`](architecture.md) · [`architecture-sequences.md`](architecture-sequences.md) · [`../mvp-spec.md`](../mvp-spec.md) (FROZEN)

This is the authoritative list of **where a large-language-model call is and is not allowed in v0**.
It expands the canonical table in [`claude-implementation-waves.md`](claude-implementation-waves.md).
If any Wave 2–4 design adds an LLM call to a row marked **No**, reject the design.

---

## v0 AI allowlist — exactly two production hops

| Event | Path | LLM call? | Quota? | Who computes money | Failure behavior |
|---|---|---|---|---|---|
| **Generate** | `POST /v1/proposals` | **Yes** — after JWT verify, after quota check passes, **after** the pricing assembler has written the user's amounts into the payload | **+1** on a saved successful generation · **0** on fail / empty / parse-fail | **FastAPI pricing assembler**, from `Users.hourly_rate` + `Packages.amount_minor`. Any `amount` / `price` the model emits is dropped and overwritten (`mvp-spec.md` §9, §16). | ≤ 1 automatic retry on parse failure; no retry storm. If nothing valid is saved → `502`, **0 quota**, nothing persisted to `proposal_json`. Token counts still recorded for cost drift. |
| **Regenerate** | `POST /v1/proposals/{id}/regenerate` | **Yes** — same preconditions, on an existing proposal; brief/notes reloaded from the server and re-guarded | **+1** on a saved success · **0** on fail | Same. Prices re-assembled from the user's *current* saved amounts before the call. | Same as Generate. On success the old `proposal_json` is replaced and `pdf_url` is nulled. |

**Both hops:** structured JSON output against a schema · `max_tokens` hard cap · system prompt
cached where the provider allows · **no streaming JSON** (wait for the object, validate, render) ·
max 1 concurrent LLM call per user · per-user + per-IP rate limit on the endpoint (`mvp-spec.md` §4, §7, §16).

---

## Everything else — FastAPI-only, no model, no quota

| Event | Path | LLM call? | Quota? | Who computes money | Failure behavior |
|---|---|---|---|---|---|
| Sign in / session | Supabase Auth (client) | No | No | — | Supabase returns no session; client re-auths. No server state changes. |
| Validate JWT | every `/v1` request | No | No | — | `401`; request rejected before any handler logic. |
| Get profile + usage | `GET /v1/me` | No | No | — | `401` / `404`. Read-only. |
| Save packages / rate / quote currency | `PUT /v1/me` | No | No | **User** types the amounts; FastAPI validates they are integer minor units in an allowed currency. | `422` on bad amounts/currency; nothing saved. |
| List proposals | `GET /v1/proposals` | No | No | — | Returns the caller's own rows only, as **view DTOs**. Bulk list+get scraping is rate-limited and logged (`mvp-spec.md` §15.2). |
| Proposal detail | `GET /v1/proposals/{id}` | No | No | — | View DTO (preview sections + form fields). **Never** the raw `proposal_json` as a promoted export. `404` if not owned. |
| Edit copy or prices | `PATCH /v1/proposals/{id}` | **No** | No | **User.** Price edits are plain writes to the allowlisted fields — they do not call the model (`mvp-spec.md` §7, §9). | `422` on a non-allowlisted key or bad value; nothing changes. On success, `pdf_url` is nulled. |
| Download / re-download PDF | `GET /v1/proposals/{id}/pdf` | No | No | — | Rendered from `proposal_json`. Cache miss → render once, store, cache `pdf_url`, return signed short-TTL URL. Cache hit → new signed URL, no re-render. Free plan → watermark on the PDF. |
| Duplicate proposal | client action → `POST /v1/proposals` later | **No** until the user hits Generate | 0 until Generate | User (unchanged). | Clone = inputs + last server `proposal_json`. The model is not called until the user explicitly Generates on the copy (`mvp-spec.md` §3.1). |
| Change status (`draft`/`sent`/`won`/`lost`) | `PATCH /v1/proposals/{id}` | No | No | — | Allowlisted field write. |
| WhatsApp share | `wa.me` deep link (client) | No | No | — | Just a URL with the PDF link. No WhatsApp Business/Cloud API in v0. |
| Follow-up email copy | server (paid plans only) | No | No | — | Text already lives in `proposal_json.followup_email` from the generate call. Free plan does not get it (`mvp-spec.md` §3.1, §15.2). |
| Create checkout session | `POST /v1/billing/checkout-session` | No | No | SKU catalog in code (`mvp-spec.md` §5.1). | `4xx` on unknown plan; no Razorpay object created. |
| Billing webhook | `POST /v1/billing/webhook` | No | No | — | HMAC verified with `hmac.compare_digest`. De-duplicated on `WebhookEvents.provider_event_id` (unique). Duplicate → `200`, no-op. Bad signature → `400`, ignored. |
| Verify email / receipts | Email adapter | No | No | — | Adapter is `mock` in CI. Send failure is logged; not user-blocking for receipts. |

---

## v1.1 — deferred AI (NOT v0)

| Event | Path | LLM call? | Quota? | Notes |
|---|---|---|---|---|
| Competitor quote extract | `POST /v1/proposals/{id}/competitor-quote` (multipart, **Pro+**) | Yes — **vision/OCR**, run **once** per upload, result cached in `CompetitorQuotes.extracted_json` | Counts as **1 generate** (so Starter cannot farm vision) | v1.1 only. Second, small text call ("position our packages vs this extract", numbers only) may follow. Tight upload limits: image ≤ 5 MB, PDF ≤ 8 pages, client-compressed (`mvp-spec.md` §17). |
| Infographic label shortening | `POST /v1/proposals/{id}/infographic` (**Pro+**) | Optional tiny LLM pass to shorten labels only | TBD | v1.1 only. Built from the same structured record (`mvp-spec.md` §10). |

---

## Invariants a reviewer can check without reading the spec cover to cover

1. **Two v0 LLM hops, both on `/v1/proposals` write paths.** Nowhere else.
2. **Money is assembled by FastAPI before the model runs** and any model-supplied amount is stripped
   on the way out. No `×1.6` / `×2.5`, no model math.
3. **Quota increments only when a successful generation is saved.** Fail / empty / parse-fail = 0 quota.
4. **`proposal_json` is a server artifact.** Clients get a view DTO. No "Export JSON".
5. **PATCH, PDF, list/detail, duplicate, checkout, webhook, login → zero model calls, zero quota.**
6. **No streaming.** The object is fully returned, validated, then rendered.
