# TP-S-006: Hosted Razorpay Checkout.js + `/auth/callback` — Test plan

| Field | Value |
|---|---|
| **Slice** | S-006 |
| **Author** | Tester |
| **Date** | 2026-08-29 |

---

## Scope

Frontend-only slice. Covers:

- The hosted Razorpay **Checkout.js** `<script>` load on `/billing` (via `next/script`, that route
  only), and the three modal callbacks — `handler` (success), `modal.ondismiss`, `payment.failed`.
- The S-004 fallback when the key is missing / mock / placeholder or Checkout.js failed to load.
- The new Next.js **`/auth/callback`** route handler — Supabase `exchangeCodeForSession` when a
  `?code=` is present, then a `303` redirect. Built/tested to the **Architect clarifications**:
  always redirect to `/` (no `next` / `redirectTo` param), every sign-in path funnels through it,
  AC 3 is a single `GET /v1/me` refetch.
- The `/sign-in` page changes: Google `redirectTo = <origin>/auth/callback`, email/password success
  hard-navigates to `/auth/callback`, `?error=` from the URL is surfaced.

**No `/v1` endpoint is added or changed. No LLM call, no quota change anywhere in this slice.** The
Razorpay HMAC webhook (S-004, frozen) stays the sole authority for the plan upgrade.

---

## Test strategy

| Layer | Tool | Focus |
|---|---|---|
| `/auth/callback` route handler | Jest (`@jest-environment node`), mocked `@supabase/ssr` + `next/headers` | code-exchange OK → `303 /`; `?error=` / failed exchange → `303 /sign-in?error=…`, no session; no code + no session → `/sign-in`; no code + session → `/`; **no `/v1` call**; **no `next` param read** |
| `/billing` page | Jest + RTL, mocked `@/lib/api`, `next/script` mocked to `null`, fake `window.Razorpay` | script loaded on this route only; Upgrade → one `POST /v1/billing/checkout-session`; modal `amount`/`currency`/`order_id` verbatim from the server response; success → pending note + one `GET /v1/me`, no client-side plan flip; dismiss → neutral note; `payment.failed` → error note + idle button; mock/placeholder key → S-004 order-summary fallback |
| `/sign-in` page | Jest + RTL, mocked Supabase client, stubbed `window.location` | Google → `signInWithOAuth({ redirectTo: <origin>/auth/callback })`; email/password success → `window.location.assign("/auth/callback")`; failed sign-in → message, no nav; `?error=` in URL → shown |
| Whole app | `tsc --noEmit`, `next build` | typecheck clean; `/auth/callback` builds as `ƒ` (dynamic); Checkout.js never executed under jsdom |
| Backend | `pytest -q` | unchanged from `main` — this slice touches no backend file |
| Docs | `git diff main` | `mvp-spec.md` + `docs/ai-touchpoints.md` byte-identical; `architecture-sequences.md` §1/§6 + `roadmap.md` + `README.md` updated |

Environment: `AI_PROVIDER=mock`, `PAYMENT_PROVIDER=mock`, `STORAGE=local`, `EMAIL_PROVIDER=mock`.
No real Razorpay key, no Supabase network — Checkout.js and Supabase Auth are stubbed / offline.

---

## AC → planned tests

| AC# | Test approach | Test ID / file |
|---|---|---|
| 1 | Automated (source scan — script referenced on `/billing` only) + Manual (real `window.Razorpay` availability needs a browser) | `frontend/src/app/__tests__/billing.test.tsx::hosted Checkout.js is loaded on /billing only — no other route references it (AC 1)` · M-004 |
| 2 | Automated | `billing.test.tsx::success handler -> pending note + a single /v1/me refetch, no client-side plan flip (AC 3, 8)` (asserts `amount` 50000, `currency` "INR", `order_id`, exactly one `checkout` call) + M-004 for the visible ₹500 |
| 3 | Automated | `billing.test.tsx::success handler -> pending note + a single /v1/me refetch, no client-side plan flip (AC 3, 8)` |
| 4 | Automated | `billing.test.tsx::modal dismiss -> neutral cancelled note, plan unchanged (AC 4)` |
| 5 | Automated | `billing.test.tsx::payment.failed -> error note with the reason, button back to idle (AC 5)` |
| 6 | Automated | `billing.test.tsx::mock key / no Checkout.js -> order-summary fallback, no crash (AC 6)` |
| 7 | Automated (one `checkout` call, no other `/v1`) + Manual (no `ai` import; `ai-touchpoints.md` diff empty) | `billing.test.tsx::success handler …` · M-001 · M-002 |
| 8 | Automated (plan stays `Free` after the success handler) + ref S-004 webhook-authority tests | `billing.test.tsx::success handler …` |
| 9 | Automated | `frontend/src/app/auth/__tests__/callback.test.ts::redirects to / after a successful code exchange (AC 9)`, `::reads no next / redirectTo param — v0 always lands on / (AC 9, ADR-004)`, `::redirects to / (not a param-supplied target) even when ?next= is present (AC 9)` |
| 10 | Automated | `callback.test.ts::redirects to /sign-in with the message when the exchange fails (AC 10)`, `::redirects to /sign-in on an ?error param without touching Supabase (AC 10)`; `sign-in.test.tsx::shows the error bounced back from /auth/callback as ?error=` |
| 11 | Automated (no code + no session → `/sign-in`) + Manual (`/auth` in middleware `PUBLIC_PATHS`) | `callback.test.ts::redirects to /sign-in when there is no code and no session (AC 11)` · M-003 |
| 12 | Automated (Google + email/password funnels) + Manual (email-verification link = Supabase dashboard redirect config) | `sign-in.test.tsx::Google sign-in redirects through /auth/callback, not / (AC 12)`, `::email/password success hard-navigates to /auth/callback so the handler runs` · M-006 |
| 13 | Automated (source scan — no `lib/api` / `apiFetch` / `/v1/` in the route handler) | `callback.test.ts::makes no /v1 call (AC 13) — the handler is pure Supabase-Auth + redirect` |
| 14 | Automated / CI | Full `npx jest` (28) + `npx tsc --noEmit` (0) + `npx next build` (`/auth/callback` = `ƒ`); `next/script` mocked to `null` in `billing.test.tsx` |
| 15 | Manual (git diff) | M-001 (`mvp-spec.md` + `ai-touchpoints.md` unchanged); `architecture-sequences.md` §1/§6, `roadmap.md`, `README.md` diffs present |

---

## Standing-invariant cases (relevant subset)

| Case | Expected | Where |
|---|---|---|
| Money never computed client-side | modal `amount` == server `amount_paise` (50000), `currency` == server `currency` ("INR"); the "₹500/mo" card is a display label only, sent nowhere | `billing.test.tsx::success handler …` |
| Client success is not authoritative | success `handler` → pending note + **one** `GET /v1/me`; `plan` stays `free`; no optimistic flip, no poll | `billing.test.tsx::success handler …` (AC 3, 8) |
| Quota untouched | success / dismiss / failure / callback all `+0`; no `UsageRecords` write path exists in this slice (frontend-only, backend unchanged) | backend `pytest -q` unchanged; `billing.test.tsx` (only `checkout` + `getMe` called) |
| No business logic in a Next.js route handler | `/auth/callback` = Supabase code-exchange + redirect only | `callback.test.ts::makes no /v1 call (AC 13)` |
| No raw `proposal_json` / "Export JSON" | not applicable — this slice renders no proposal / preview / PDF | n/a |
| `docs/ai-touchpoints.md` still true | two AI hops only; "Sign in / session", "Create checkout session", "Billing webhook" rows all `No / No` | M-001, M-002 |

---

## Edge cases

- `/auth/callback?code=…&next=/billing` — `next` is **ignored**, redirect is still `/` (AC 9 clarification).
- `/auth/callback` with an `error_description` param — preferred over `error` for the `/sign-in?error=` message.
- Mock/placeholder key (`key.includes("mock")`) **or** `window.Razorpay` undefined (script not loaded) — both take the S-004 order-summary fallback; no crash, no unhandled rejection.
- `payment.failed` with no `error.description` — note falls back to "please try again".
- Email/password path: hard nav (`window.location.assign`), not `router.push`, so the route handler actually runs with the fresh session cookie.

---

## Manual checklist

- [ ] M-001: `git diff main -- mvp-spec.md docs/ai-touchpoints.md` is empty (byte-identical).
- [ ] M-002: `frontend/src/app/billing/page.tsx` and `frontend/src/app/auth/callback/route.ts` import
      no `lib/ai` / `services.ai` / generation / LLM module; the only network calls are `api.checkout`,
      `api.getMe`, Razorpay-hosted Checkout.js, and the Supabase code-exchange.
- [ ] M-003: `frontend/src/lib/supabase/middleware.ts` `PUBLIC_PATHS` contains `/auth`, so
      `/auth/callback` is reachable with no session.
- [ ] M-004: **(pre-launch, live keys)** With a real `NEXT_PUBLIC_RAZORPAY_KEY_ID` + test Razorpay
      keys, `/billing` → "Upgrade to Starter" opens the hosted modal showing **₹500**; success shows
      the pending note; the webhook flips the plan to Starter on the next `/billing` load.
- [ ] M-005: **(pre-launch, live Supabase)** Real Google OAuth round-trip lands the user on `/`
      signed in; the PKCE `code` is exchanged in `/auth/callback`.
- [ ] M-006: **(pre-launch, config)** Supabase project "Site URL" / redirect allow-list points
      email-verification + magic links at `<origin>/auth/callback`.
- [ ] M-007: Full `cd frontend && npx jest` green; `cd backend && python -m pytest -q` unchanged from `main`.

---

## Environment notes

- `next/script` is mocked to `() => null` in `billing.test.tsx` — Checkout.js is never fetched or
  executed under jsdom (AC 14).
- `callback.test.ts` runs under `@jest-environment node` with `@supabase/ssr` and `next/headers` mocked;
  no Supabase network.
- Backend is not started for any frontend test; `@/lib/api` is mocked.
