# Slice: S-004 — Razorpay live rail + web money/PDF wiring

| Field | Value |
|---|---|
| **Slice ID** | S-004 |
| **Phase** | 2 AI + money |
| **Status** | Accepted |
| **Owner** | PM / 2026-08-29 |

> **Wave 4, second half.** Swap the mock payment adapter for a real Razorpay port (Orders API + HMAC
> webhook), and wire the web client to the real cached PDF and the upgrade flow. `mock` stays the
> default and the only thing CI runs — no live Razorpay keys anywhere. **No LLM call is added to
> checkout, webhook, or PDF.**

---

## User story

**As an** India-based freelancer on Free
**I want** to download my proposal as a PDF and upgrade to Starter with a real payment
**So that** I can send clean proposals and lift my monthly limit

---

## Acceptance criteria

**Razorpay backend (`PAYMENTS_PROVIDER=razorpay`)**

1. **Given** `PAYMENTS_PROVIDER=razorpay` without the 3 keys, **when** the app boots, **then**
   `validate_startup_config` raises. `mock` still needs nothing.
2. **Given** `create_order`, **when** called, **then** it POSTs to `{RAZORPAY_API_BASE}/orders` with
   HTTP Basic auth (`key_id`:`key_secret`), `amount` in paise, and `notes` carrying `user_id` +
   `plan_id`; the response `id` becomes `provider_order_id`.
3. **Given** a Razorpay-shaped webhook body with a valid `X-Razorpay-Signature`
   (`hmac_sha256(webhook_secret, raw_body)` hex), **when** verified, **then** `plan_id` and `user_id`
   are read from `payload.order.entity.notes`; a wrong signature → `None` → `400`.
4. **Given** a paid Razorpay event for a user, **when** the webhook is processed, **then** the user's
   `plan_id` becomes `starter_inr`, a `Subscription` row is written, the usage period re-anchors, and
   a replay of the same `provider_event_id` is a `200` no-op — **the same `billing.handle_webhook`
   code path as the mock** (HMAC + `WebhookEvents` idempotency + anchor).
5. **Given** the webhook route, **when** it runs, **then** it accepts `X-Razorpay-Signature`
   (real) and `X-Signature` (mock/tests).
6. **Given** the whole slice, **then** **no LLM call and no quota** on checkout or webhook
   (`docs/ai-touchpoints.md` unchanged).

**Web client**

7. **Given** the editor, **when** I click "Download PDF", **then** `GET /v1/proposals/{id}/pdf` is
   called and the returned `pdf_url` is opened (relative URLs resolved against the API origin).
8. **Given** a `/billing` page, **when** I open it, **then** it shows my current plan + usage and the
   Starter offer (₹500 / 20).
9. **Given** `/billing`, **when** I click "Upgrade to Starter", **then** `POST
   /v1/billing/checkout-session` is called; if `window.Razorpay` + a real key are present the hosted
   checkout opens, otherwise the created order id + amount are shown (the webhook is what upgrades).
10. **Given** a `402` on generate or regenerate, **then** an "Upgrade" link to `/billing` is shown.
11. **Given** CI, **then** `typecheck` + `jest` + `next build` pass with no backend and no real keys.

---

## Out of scope

- Hosted Razorpay Checkout.js `<script>` load + success/failure handlers, `/auth/callback` route
  (roadmap — "Razorpay Checkout.js integration").
- Subscriptions API (recurring) — v0 uses one-time orders per period; recurring is later.
- Real signed storage URLs (roadmap, tracked from S-003).
- Global `$` rail / Stripe (roadmap).

---

## Dependencies

- `S-003` (Accepted) — the PDF endpoint and the `notes`-carrying `create_order` signature.

---

## Definition of done (PM)

- [x] All 11 AC verified in the test report (61 backend + 12 Jest)
- [x] `PAYMENTS_PROVIDER=mock` stays the CI default; no live Razorpay keys in CI
- [x] `docs/ai-touchpoints.md` + `mvp-spec.md` unchanged (verified `git diff --stat` empty)
- [x] `docs/roadmap.md` gains the follow-ups; `README.md` status updated
- [x] Parity check passes (no SYNC_GROUP file touched)
- [x] PM `Status: Accepted`

**PM acceptance (2026-08-29):** The live Razorpay port reuses the exact webhook code the mock proved
(HMAC + idempotency + anchor), so AC 4 is a provider swap, not new money logic. Checkout and webhook
have no LLM anywhere near them. The web client's PDF and upgrade paths are thin and tested. Hosted
checkout.js is a deliberate finishing-touch deferral. **Accepted.**

---

## Technical specification (Architect)

### Files

```
backend/app/services/payments/
  razorpay.py              # RazorpayPaymentProvider — Orders API (httpx) + HMAC webhook
  base.py                  # WebhookEvent gains `notes: dict`; create_order gains `notes`
  mock.py __init__.py      # register "razorpay"; key check; mock lifts top-level fields into notes
backend/app/services/billing.py     # create_order(notes=...); _user_id_from_event reads notes
backend/app/routers/billing.py      # webhook accepts X-Razorpay-Signature | X-Signature

frontend/src/lib/api.ts             # + getPdf(id), apiOrigin(); checkout() returns key_id/plan_id
frontend/src/app/billing/page.tsx   # NEW — plan + usage + Upgrade
frontend/src/app/proposals/[id]/page.tsx   # Download PDF -> api.getPdf -> window.open; 402 -> /billing
frontend/src/app/proposals/new/page.tsx    # 402 -> /billing link
frontend/src/app/page.tsx           # "Plan & billing" link
```

### Inference & money (cross-ref `docs/ai-touchpoints.md`)

- **No LLM anywhere in this slice.** Checkout = one Orders API POST. Webhook = HMAC verify +
  `WebhookEvents` upsert + plan/period write. PDF download = `GET .../pdf` (S-003, no LLM, no quota).
- **Money:** unchanged — plan prices come from the in-code catalog (`payments/catalog.py`,
  `mvp-spec.md` §5.1); the webhook only flips `user.plan_id`. `ai-touchpoints.md` accurate as written.

### Razorpay port

`create_order`: `httpx.AsyncClient` (the app's own `httpx`, not the SDK's `httpx2`) → `POST /orders`
with `auth=(key_id, key_secret)`. `verify_webhook`: `hmac_util.signatures_match` (hex SHA-256) — the
identical function the mock uses — then parse `payload.{order,payment,subscription}.entity`. User +
plan travel in `notes` (set on the order, echoed by Razorpay on the event).

### Web

`api.getPdf(id)` → `{pdf_url}`; the editor resolves a relative `pdf_url` against `apiOrigin()` (the
API base minus `/v1`) and `window.open`s it. `/billing` calls `api.checkout("starter_inr")`; a real
`window.Razorpay` + `NEXT_PUBLIC_RAZORPAY_KEY_ID` opens hosted checkout, else the order summary is
shown. `402` handlers set an `overQuota` flag that renders a `<Link href="/billing">`.

### Architect checklist

- [x] No `/v1` contract change (checkout response gains `key_id` / `plan_id` fields — additive)
- [x] No new LLM call; `docs/ai-touchpoints.md` still accurate
- [x] Webhook is the same `handle_webhook` for mock + razorpay (HMAC + idempotency + anchor)
- [x] `mock` + local remain the CI default; `razorpay` gated by a startup key check
- [x] No secrets — `.env.example` / compose use `${VAR:-}`; frontend key is `NEXT_PUBLIC_*` (public by design)

### Risks / tradeoffs

- **One-time orders, not the Subscriptions API** — the webhook re-anchors a 30-day window per paid
  event. Recurring billing is a later slice.
- **Hosted checkout.js not wired** — `/billing` degrades to showing the order; the webhook still
  upgrades. Acceptable for the skeleton; roadmap item filed.
- **`httpx` (0.28) vs the SDK's `httpx2`** — both installed, separate packages; the Razorpay port
  uses plain `httpx` deliberately.

---

## Links

- Test plan: [`TP-S-004-razorpay-and-web-money.md`](../test-plans/TP-S-004-razorpay-and-web-money.md)
- Test report: [`TR-S-004-razorpay-and-web-money.md`](../test-reports/TR-S-004-razorpay-and-web-money.md)
- ADR: none (webhook contract unchanged from S-001; model/PDF decisions in ADR-002)

---

## Changelog

| Date | Agent | Change |
|---|---|---|
| 2026-08-29 | PM | 11 AC — Razorpay port, same webhook path, web PDF + upgrade, 402 → /billing |
| 2026-08-29 | Architect | `notes`-carried user/plan; reuse `handle_webhook`; web wiring + graceful checkout fallback |
| 2026-08-29 | Builder | `razorpay.py`, `base`/`mock`/`__init__` updates, billing route header, `/billing` page, PDF + 402 wiring |
| 2026-08-29 | Tester | 61 backend (+5) + 12 Jest (+4); Razorpay Orders API + checkout.js fully stubbed → Ship |
| 2026-08-29 | PM | Provider swap reuses the proven webhook path; no LLM near money → **Accepted** |
