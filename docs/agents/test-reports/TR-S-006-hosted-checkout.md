# TR-S-006: Hosted Razorpay Checkout.js + `/auth/callback` — Test report

| Field | Value |
|---|---|
| **Slice** | S-006 |
| **Author** | Tester |
| **Date** | 2026-08-29 |
| **Branch / commit under test** | `s-006-hosted-checkout` @ `a5c64ff` |
| **Recommendation** | **Ship** |

---

## Summary

All **15 acceptance criteria** are covered — 13 fully automated, 2 with a manual pre-launch component
(the real Razorpay modal and the real Supabase OAuth round-trip, neither runnable in CI without live
keys — see M-004/M-005).

**28 frontend Jest tests** pass (was 25 on the Builder commit; **+3 added by the Tester**):

- AC 1 — a source-scan test proving `checkout.razorpay.com/v1/checkout.js` is referenced by
  `billing/page.tsx` **and no other route** (the "no other route loads that script" clause had no
  coverage).
- AC 2 — the success test now also asserts modal `currency == "INR"` and **exactly one**
  `checkout-session` call for the whole flow (money invariant + AC 7).
- AC 9 — a source-scan test that the route handler reads **no** `next` / `redirectTo` param, plus a
  behavioural test that `/auth/callback?code=…&next=/billing` still redirects to `/` (the Architect
  clarification narrowing AC 9).

`tsc --noEmit` is clean; `next build` produces 9 routes with `/auth/callback` as `ƒ` (dynamic).
Backend `pytest -q` is **61 passed — identical to `main`** (this slice touches no backend file).
`mvp-spec.md` and `docs/ai-touchpoints.md` are **byte-identical to `main`** (`git diff` empty).

The webhook (S-004, frozen) remains the only thing that upgrades a plan: the browser success handler
shows a pending note and does a single `GET /v1/me` — asserted to **not** flip the plan client-side.
No LLM import and no quota path exists in `billing/page.tsx` or `auth/callback/route.ts`.

**No production bug found.** One non-blocking doc nit (README + roadmap status strings lag the Builder
commit) — listed under Gaps.

---

## AC coverage matrix

| AC# | Description | Type | Test reference | Result |
|---|---|---|---|---|
| 1 | Hosted Checkout.js `<script>` loaded via `next/script` on `/billing`; **no other route** loads it | A + M | `billing.test.tsx::hosted Checkout.js is loaded on /billing only — no other route references it (AC 1)`; `window.Razorpay` actually available → M-004 | Pass |
| 2 | Real key → one `POST /v1/billing/checkout-session`; modal opens with server `provider_order_id`, `amount_paise`, `currency` (INR), key; amount never computed client-side | A + M | `billing.test.tsx::success handler -> pending note + a single /v1/me refetch … (AC 3, 8)` (asserts `amount`=50000, `currency`="INR", `order_id`, one `checkout` call); visible ₹500 → M-004 | Pass |
| 3 | Success handler → "Payment received — your plan updates in a moment" + one `GET /v1/me` refetch; no client-side plan flip | A | `billing.test.tsx::success handler -> pending note + a single /v1/me refetch, no client-side plan flip (AC 3, 8)` | Pass |
| 4 | `modal.ondismiss` → neutral "Checkout cancelled" note, no error styling, plan/usage unchanged | A | `billing.test.tsx::modal dismiss -> neutral cancelled note, plan unchanged (AC 4)` | Pass |
| 5 | `payment.failed` → error note with the Razorpay reason, button back to idle, retry without reload | A | `billing.test.tsx::payment.failed -> error note with the reason, button back to idle (AC 5)` | Pass |
| 6 | Missing / mock / placeholder key **or** script load failure → S-004 order-summary fallback, no crash, no unhandled rejection | A | `billing.test.tsx::mock key / no Checkout.js -> order-summary fallback, no crash (AC 6)` | Pass |
| 7 | Only `/v1` call is `POST /v1/billing/checkout-session`; no LLM, no quota (success = +0, failure = +0) | A + M | `billing.test.tsx::success handler …` (only `checkout` + `getMe` called, one `checkout`); M-001 (`ai-touchpoints.md` diff empty), M-002 (no `ai` import) | Pass |
| 8 | Browser success but no webhook → `plan_id` stays `free`, usage unchanged; client success never mutates server state | A | `billing.test.tsx::success handler …` (plan still `Free` after handler); webhook-authority proven in S-004 `test_billing.py` / `test_razorpay.py` (unchanged) | Pass |
| 9 | `/auth/callback` exchanges `?code=` via `@supabase/ssr`; on success redirects to `/` **unconditionally** (no `next` param — Architect clarification) | A | `callback.test.ts::redirects to / after a successful code exchange (AC 9)`, `::reads no next / redirectTo param — v0 always lands on / (AC 9, ADR-004)`, `::redirects to / (not a param-supplied target) even when ?next= is present (AC 9)` | Pass |
| 10 | `?error=` param or failed exchange → redirect to `/sign-in` with a visible error message, no session | A | `callback.test.ts::redirects to /sign-in with the message when the exchange fails (AC 10)`, `::redirects to /sign-in on an ?error param without touching Supabase (AC 10)`; `sign-in.test.tsx::shows the error bounced back from /auth/callback as ?error=` | Pass |
| 11 | No `?code=` and no session → redirect to `/sign-in`; route publicly reachable | A + M | `callback.test.ts::redirects to /sign-in when there is no code and no session (AC 11)`; `/auth` in `middleware.ts` `PUBLIC_PATHS` → M-003 | Pass |
| 12 | Every post-auth path funnels through `/auth/callback`: Google `redirectTo`, email/password hard-nav (and email-verification link via config) | A + M | `sign-in.test.tsx::Google sign-in redirects through /auth/callback, not / (AC 12)`, `::email/password success hard-navigates to /auth/callback so the handler runs`; email-verification link config → M-006 | Pass |
| 13 | Callback makes **no** `/v1` call and adds no business logic to the route handler — code-exchange + redirect only | A | `callback.test.ts::makes no /v1 call (AC 13) — the handler is pure Supabase-Auth + redirect` | Pass |
| 14 | CI (no real key, mock Supabase): `typecheck` + `jest` + `next build` pass; Checkout.js not executed under jsdom; `/billing` asserts AC 6 fallback; callback asserts AC 10 | A / CI | `npx jest` (28), `npx tsc --noEmit` (0), `npx next build` (9 routes); `next/script` mocked to `null` in `billing.test.tsx` | Pass |
| 15 | `mvp-spec.md` untouched; `ai-touchpoints.md` unchanged; `architecture-sequences.md` §1/§6, `roadmap.md`, `README.md` updated | M | M-001 (`git diff main -- mvp-spec.md docs/ai-touchpoints.md` empty); `architecture-sequences.md` §1 (callback hop) + §6 (hosted-script note), `roadmap.md` row, `README.md` row all present in `git diff main` | Pass |

**Coverage:** 15 / 15 AC mapped — 13 automated, 2 automated + manual pre-launch component (M-004 real Razorpay modal, M-005 real Supabase OAuth).

---

## Backend tests

### Added / changed

None — this slice touches no backend file.

### Run output

```
$ cd backend && PYTHONPATH=. python -m pytest -q
.............................................................            [100%]
61 passed in ~16s
```

Identical to `main` (S-004 baseline was 61). No regression.

---

## Frontend tests

### Added by the Tester (+3, in the Builder's existing files)

- `src/app/__tests__/billing.test.tsx`
  - `hosted Checkout.js is loaded on /billing only — no other route references it (AC 1)` — walks
    `src/app/**`, asserts `checkout.razorpay.com` appears **only** in `billing/page.tsx`.
  - existing `success handler …` test strengthened: also asserts modal `currency == "INR"` and
    exactly one `checkout` call (AC 2 / AC 7 money invariant).
- `src/app/auth/__tests__/callback.test.ts`
  - `reads no next / redirectTo param — v0 always lands on / (AC 9, ADR-004)` — source scan.
  - `redirects to / (not a param-supplied target) even when ?next= is present (AC 9)` — behavioural.

### Builder's tests (verified green)

- `src/app/auth/__tests__/callback.test.ts` — 6 original (code-exchange → `/`; failed exchange /
  `?error=` → `/sign-in?error=`; no code + no session → `/sign-in`; no code + session → `/`; no `/v1`
  call).
- `src/app/__tests__/sign-in.test.tsx` — 4 (Google `redirectTo`; email/password hard-nav; `?error=`
  shown; failed sign-in shows message, no nav).
- `src/app/__tests__/billing.test.tsx` — 6 (plan + offer render; AC 6 fallback; success handler; AC 4
  dismiss; AC 5 `payment.failed`).

### Run output

```
$ cd frontend && npx jest
PASS src/app/auth/__tests__/callback.test.ts
PASS src/lib/__tests__/api.test.ts
PASS src/components/__tests__/PreviewPane.test.tsx
PASS src/components/__tests__/SectionForms.test.tsx
PASS src/app/__tests__/sign-in.test.tsx
PASS src/app/__tests__/billing.test.tsx
Test Suites: 6 passed, 6 total
Tests:       28 passed, 28 total

$ npx tsc --noEmit          # exit 0

$ NEXT_PUBLIC_API_BASE_URL=… NEXT_PUBLIC_SUPABASE_URL=… NEXT_PUBLIC_SUPABASE_ANON_KEY=… npx next build
 ✓ Compiled successfully
Route (app)                              Size     First Load JS
┌ ○ /                                    2.14 kB         148 kB
├ ○ /_not-found                          979 B           106 kB
├ ƒ /auth/callback                       135 B           106 kB
├ ○ /billing                             4.25 kB         150 kB
├ ƒ /proposals/[id]                      3.79 kB         150 kB
├ ○ /proposals/new                       3.12 kB         149 kB
├ ○ /settings                            2.64 kB         149 kB
└ ○ /sign-in                             1.03 kB         143 kB
```

`/auth/callback` builds as `ƒ` (server-rendered on demand) — correct for a route handler that reads
cookies + query params.

---

## Manual / integration

| ID | Check | Result |
|---|---|---|
| M-001 | `git diff main -- mvp-spec.md docs/ai-touchpoints.md` empty (byte-identical) | Pass |
| M-002 | No LLM / generation import in `billing/page.tsx` or `auth/callback/route.ts`; only network calls are `api.checkout`, `api.getMe`, Razorpay Checkout.js, Supabase code-exchange | Pass |
| M-003 | `middleware.ts` `PUBLIC_PATHS = ["/sign-in", "/auth"]`; `path.startsWith("/auth/")` matches `/auth/callback` → reachable pre-session | Pass |
| M-004 | **Pre-launch (live Razorpay test keys):** hosted modal shows ₹500, success → pending note, webhook flips plan to Starter | Deferred — no CI keys by design |
| M-005 | **Pre-launch (live Supabase):** real Google OAuth round-trip lands signed-in on `/`; PKCE `code` exchanged in `/auth/callback` | Deferred — no CI Supabase by design |
| M-006 | **Pre-launch (config):** Supabase Site URL / redirect allow-list points email links at `<origin>/auth/callback` | Deferred — dashboard config |
| M-007 | Full `npx jest` (28) green; backend `pytest -q` (61) unchanged | Pass |

---

## Regressions

None.

- Backend `pytest -q` — 61 passed, identical to `main`.
- Pre-existing frontend suites (`api.test.ts`, `PreviewPane.test.tsx`, `SectionForms.test.tsx`) —
  unchanged and green.
- `/billing` still renders the current plan + Starter offer + "₹500/mo" label (S-004 behaviour);
  the fallback path is byte-for-byte the S-004 order-summary note.
- No `/v1` contract touched; `docs/ai-touchpoints.md` invariants (two AI hops; checkout / webhook /
  login → zero model calls, zero quota) still hold.

---

## Gaps / rework items

**Blocking:** none.

**Non-blocking:**

1. **README + roadmap status strings lag the Builder commit.** `README.md`
   ("**Specified** — … Builder pending") and the `roadmap.md` Checkout.js row
   ("S-006 (Specified, Builder pending)") still read as pre-Builder. AC 15 only requires
   `mvp-spec.md` + `ai-touchpoints.md` unchanged (met) and `architecture-sequences.md` / `roadmap.md`
   updated (met — the row was repointed to S-006). PM to refresh the status wording on acceptance.
2. **M-004 / M-005 / M-006 are pre-launch manual checks** — the real Razorpay modal, the real
   Supabase OAuth round-trip, and the Supabase redirect config cannot run in CI without live keys.
   This is the expected v0 posture (same as S-004's "no live Razorpay smoke test" gap) and belongs
   on the pre-launch checklist, not this slice.
3. **Email-verification-link funnel is config, not code** — AC 12's third path relies on the Supabase
   dashboard redirect allow-list (M-006). The code side (the route handler exchanging a `?code=` from
   any source) is fully tested.

---

## Sign-off

- [x] All 15 AC mapped to tests (13 A, 2 A + manual pre-launch component)
- [x] Auth: `/auth/callback` — no code + no session → `/sign-in`; failed exchange / `?error=` →
      `/sign-in?error=` with no session (automated)
- [x] Ownership: n/a — this slice adds no `/v1` route and reads no proposal
- [x] Money invariant tested — modal `amount` == server `amount_paise` (50000), `currency` == server
      `currency`; nothing computed client-side; the ₹500 card is a display label sent nowhere
- [x] Webhook stays the sole plan-upgrade authority — client success = pending note + one
      `GET /v1/me`, no optimistic flip (automated)
- [x] `docs/ai-touchpoints.md` still matches the code — no LLM / quota path added; `git diff` empty
- [x] `mvp-spec.md` untouched — `git diff` empty
- [x] Ready for PM acceptance
