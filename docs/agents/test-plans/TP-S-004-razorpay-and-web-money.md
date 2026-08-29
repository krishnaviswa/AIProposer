# TP-S-004: Razorpay live rail + web money/PDF — Test plan

| Field | Value |
|---|---|
| **Slice** | S-004 |
| **Author** | Tester |
| **Date** | 2026-08-29 |

---

## Scope

The `RazorpayPaymentProvider` (Orders API stubbed) + HMAC webhook, the shared `billing.handle_webhook`
path under `PAYMENTS_PROVIDER=razorpay`, and the web client's PDF-download + `/billing` upgrade flow.
No live Razorpay keys, no `checkout.js`, no backend for the Jest tests.

---

## Test strategy

| Layer | Tool | Focus |
|---|---|---|
| Razorpay port | pytest + `monkeypatch` on `razorpay.httpx.AsyncClient` | Orders POST shape (URL, basic auth, amount, notes); webhook HMAC + `notes` extraction; paid vs non-paid events |
| Billing e2e | pytest through `POST /v1/billing/{checkout-session,webhook}` with `PAYMENTS_PROVIDER=razorpay` | order created; signed Razorpay-shaped webhook → plan upgrade + period re-anchor |
| Startup | pytest | `razorpay` without keys → boot fails |
| Web API | Jest + `fetch` mock | `getPdf` path; `checkout` posts `{plan_id}`; `apiOrigin` strips `/v1` |
| Web billing page | Jest + RTL + mocked `@/lib/api` | renders plan + Starter offer; Upgrade → `api.checkout`; mock key → order note shown |
| Whole app | `tsc --noEmit`, `next build` | 8 routes incl. `/billing`, no backend, fake `NEXT_PUBLIC_*` |

---

## AC → tests

| AC# | Test |
|---|---|
| 1 | `test_razorpay.py::test_startup_requires_keys` |
| 2 | `test_razorpay.py::test_create_order_calls_orders_api` |
| 3 | `test_razorpay.py::test_webhook_signature_and_note_extraction`, `::test_webhook_non_paid_event_is_not_paid` |
| 4 | `test_razorpay.py::test_checkout_and_webhook_end_to_end_with_razorpay`; idempotency reuses `test_billing.py::test_webhook_upgrades_plan_and_is_idempotent` (mock, same code path) |
| 5 | `test_razorpay.py::test_checkout_and_webhook_end_to_end_with_razorpay` (sends `X-Signature`); real header covered by the same `handle_webhook` |
| 6 | Manual — `git diff docs/ai-touchpoints.md` empty; no `ai`/`generation` import in `billing`/`payments` |
| 7 | `frontend/src/lib/__tests__/api.test.ts::getPdf hits the proposal pdf path …` |
| 8–9 | `frontend/src/app/__tests__/billing.test.tsx` (2 tests) |
| 10 | Manual — `overQuota` → `<Link href="/billing">` in `proposals/new` + `proposals/[id]` |
| 11 | Manual/CI — `npm run typecheck && npm test && npm run build` |

---

## Manual checklist

- [ ] M-001: `git diff --stat docs/ai-touchpoints.md mvp-spec.md` empty
- [ ] M-002: `grep -r "services.ai\|generation" backend/app/services/payments backend/app/services/billing.py backend/app/routers/billing.py` — no matches (no LLM near money)
- [ ] M-003: `402` on `/proposals/new` and `/proposals/[id]` renders the `/billing` link
- [ ] M-004: `npm run typecheck` (0), `npm test` (12 pass), `npm run build` (8 routes incl. `/billing`)
- [ ] M-005: full backend `pytest -q` green on `PAYMENTS_PROVIDER=mock`
