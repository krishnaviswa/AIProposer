# TR-S-004: Razorpay live rail + web money/PDF — Test report

| Field | Value |
|---|---|
| **Slice** | S-004 |
| **Author** | Tester |
| **Date** | 2026-08-29 |
| **Recommendation** | **Ship** |

---

## Summary

**61 backend pytest tests** (was 56; +5 Razorpay) and **12 frontend Jest tests** (was 8; +4) pass.
`tsc --noEmit` clean; `next build` produces 8 routes including `/billing`. All 11 acceptance criteria
green. The live `RazorpayPaymentProvider` verifies webhooks with the **exact same
`hmac_util.signatures_match`** the mock uses and feeds the **same `billing.handle_webhook`** (HMAC +
`WebhookEvents` idempotency + period anchor) — so turning Razorpay on is a provider swap, not new
money logic. No LLM import exists anywhere in `payments/`, `billing.py`, or the billing router
(verified by grep). `docs/ai-touchpoints.md` and `mvp-spec.md` are byte-identical.

---

## AC coverage matrix

| AC# | Description | Type | Test reference | Result |
|---|---|---|---|---|
| 1 | `razorpay` without the 3 keys fails boot; `mock` needs nothing | A | `test_razorpay.py::test_startup_requires_keys` | Pass |
| 2 | `create_order` POSTs `/orders` with basic auth, paise amount, `notes` | A | `test_razorpay.py::test_create_order_calls_orders_api` | Pass |
| 3 | Webhook HMAC verify; `plan_id`/`user_id` from `order.entity.notes`; bad sig → `None` | A | `test_razorpay.py::test_webhook_signature_and_note_extraction` | Pass |
| 3 | Non-paid event → `paid=False` | A | `test_razorpay.py::test_webhook_non_paid_event_is_not_paid` | Pass |
| 4 | Paid event → plan `starter_inr`, `Subscription` row, period re-anchor (`included`→20); replay = `200` no-op | A | `test_razorpay.py::test_checkout_and_webhook_end_to_end_with_razorpay`; idempotency via `test_billing.py::test_webhook_upgrades_plan_and_is_idempotent` (same `handle_webhook`) | Pass |
| 5 | Route accepts `X-Razorpay-Signature` and `X-Signature` | A | `test_razorpay.py` e2e sends `X-Signature`; `routers/billing.py` header aliases both | Pass |
| 6 | No LLM / no quota on checkout or webhook | M | M-002 (grep: no `services.ai` / `generation` import in `payments/`, `billing.py`, billing router) | Pass |
| 7 | "Download PDF" → `GET .../pdf`; relative URL resolved against API origin | A | `frontend/src/lib/__tests__/api.test.ts::getPdf hits the proposal pdf path …`, `::apiOrigin strips the trailing /v1` | Pass |
| 8 | `/billing` shows current plan + usage + Starter offer | A | `frontend/src/app/__tests__/billing.test.tsx::shows the current plan and the Starter offer` | Pass |
| 9 | Upgrade → `api.checkout("starter_inr")`; mock key → order note | A | `billing.test.tsx::Upgrade calls the checkout API and (mock key) shows the order note` | Pass |
| 10 | `402` → `/billing` link | M | M-003 (`overQuota` state → `<Link href="/billing">` in `proposals/new` + `proposals/[id]`) | Pass |
| 11 | `typecheck` + `jest` + `build` green, no backend, no real keys | A/M | M-004 | Pass |

**Coverage:** 11 / 11 AC — 8 automated, 3 review/build.

---

## Backend tests

### Added / changed (5 net new)

- `tests/test_razorpay.py` — 5 tests: webhook signature + `notes` extraction, non-paid event,
  `create_order` Orders-API shape (stubbed httpx), startup key check, checkout + webhook e2e under
  `PAYMENTS_PROVIDER=razorpay`.
- `payments/base.py` — `WebhookEvent` gains `notes: dict`; `create_order` gains `notes`. `mock.py`
  lifts top-level `receipt`/`notes` into `event.notes` so `test_billing.py` (unchanged) still passes.
- `billing.py::_user_id_from_event` reads `event.notes["user_id"]` then `receipt`.
- `routers/billing.py` webhook accepts `X-Razorpay-Signature | X-Signature`.

### Run output

```
$ cd backend && PYTHONPATH=. python -m pytest -q
.............................................................            [100%]
61 passed in ~4s
```

---

## Frontend tests

### Added / changed (4 net new)

- `src/lib/__tests__/api.test.ts` — `getPdf` path, `checkout` body, `apiOrigin` strips `/v1`.
- `src/app/__tests__/billing.test.tsx` — 2 tests: plan + Starter offer render; Upgrade → `api.checkout`
  → order note (mock key).

### Run output

```
$ cd frontend && npx jest
Test Suites: 4 passed, 4 total
Tests:       12 passed, 12 total

$ npx tsc --noEmit      # exit 0
$ npx next build        # ✓ 8 routes incl. /billing
```

---

## Manual / integration

| ID | Check | Result |
|---|---|---|
| M-001 | `git diff --stat docs/ai-touchpoints.md mvp-spec.md` empty | Pass |
| M-002 | No `services.ai` / `generation` import in `payments/`, `billing.py`, billing router | Pass |
| M-003 | `402` on `/proposals/new` + `/proposals/[id]` renders the `/billing` link | Pass |
| M-004 | `typecheck` + `jest` (12) + `build` (8 routes) | Pass |
| M-005 | Backend `pytest -q` green on `PAYMENTS_PROVIDER=mock` | Pass |

---

## Regressions

None. `test_billing.py` (mock webhook) unchanged and green — the `notes` field is additive and the
mock lifts its flat payload fields into it.

---

## Gaps / rework items (non-blocking)

1. **Hosted Razorpay Checkout.js not wired** — `/billing` degrades to showing the order id + amount;
   the webhook still upgrades the plan. Roadmap: "Razorpay Checkout.js integration + `/auth/callback`".
2. **One-time orders, not the Subscriptions API** — the webhook re-anchors a 30-day window per paid
   event; true recurring billing is later.
3. **`LocalStorageProvider.signed_url`** still returns a path (from S-003) — roadmap.
4. **No live Razorpay smoke test** — CI has no keys by design; a manual `PAYMENTS_PROVIDER=razorpay`
   run against test keys is a pre-launch checklist item.

---

## Sign-off

- [x] All 11 AC mapped (8 automated, 3 review/build)
- [x] Live Razorpay reuses the proven `handle_webhook` (HMAC + idempotency + anchor) — asserted e2e
- [x] No LLM call and no quota on checkout / webhook / PDF — verified by grep + tests
- [x] `docs/ai-touchpoints.md` + `mvp-spec.md` unchanged — verified
- [x] Ready for PM acceptance
