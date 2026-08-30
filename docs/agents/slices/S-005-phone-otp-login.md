# Slice: S-005 — Phone OTP as an optional login method

| Field | Value |
|---|---|
| **Slice ID** | S-005 |
| **Phase** | 1 Platform skeleton (auth) |
| **Status** | Accepted |
| **Owner** | PM / 2026-08-29 |

> Product decision 2026-08-29: add phone OTP as an **optional** sign-in method. Alternative sign-in
> (phone-only accounts allowed), MSG91 as the +91 SMS provider, **frozen `mvp-spec.md` untouched** —
> the roadmap row moves `blocked-on-decision` → `feature-flag`. Full rationale in
> [`ADR-003`](../adrs/ADR-003-optional-phone-otp-login.md).

---

## User story

**As a** freelancer in India without a habitual email inbox
**I want** to sign in with my phone number and an SMS code
**So that** I can start quoting without creating or verifying an email account.

---

## Acceptance criteria

1. **Given** `AUTH_PHONE_OTP` is off (the default), **when** a request presents a valid Supabase JWT
   whose only identity claim is `phone` (no `email`), **then** FastAPI returns `401`
   ("Phone sign-in is not enabled") and provisions no row.
2. **Given** `AUTH_PHONE_OTP` is on, **when** the same phone-only JWT is presented for the first time,
   **then** a `users` row is provisioned with `phone` set, `email` null, `plan_id = free`, and
   `GET /v1/me` returns `200` with `phone` populated and `email: null`.
3. **Given** an existing email account, **when** the same `sub` later presents a token that also
   carries a `phone` claim (account enabled phone as a second method in Supabase), **then** the
   `phone` is backfilled onto that row and no second row is created.
4. **Given** a valid JWT with **neither** `email` nor `phone`, **then** FastAPI returns `401`.
5. **Given** email/password and Google sign-in, **then** behaviour is unchanged — `GET /v1/me`
   returns the email, `phone` is `null`, and no phone field renders on `/sign-in` unless
   `NEXT_PUBLIC_AUTH_PHONE_OTP === "true"`.
6. **Given** `NEXT_PUBLIC_AUTH_PHONE_OTP` is true, **when** the user enters a phone number and the
   SMS code on `/sign-in`, **then** the client calls `supabase.auth.signInWithOtp` then
   `verifyOtp({ type: "sms" })` and, on success, hard-navigates to `/auth/callback` — the same
   funnel every other sign-in path uses (S-006, [`ADR-004`](../adrs/ADR-004-auth-redirect-callback.md));
   the callback confirms the session and redirects to `/`.
7. **No** `/v1` endpoint is added. **No** LLM call and **no** quota change anywhere near sign-in
   (`docs/ai-touchpoints.md` row "Sign in / session" and "Validate JWT" unchanged).
8. Alembic migration `0002` adds `users.phone` (nullable, indexed) and makes `users.email` nullable;
   `downgrade` reverses both. No `create_all`.

---

## UX notes

- Route(s): `/sign-in` only.
- States: default (email + Google) / phone entry / code entry / error (Supabase message shown inline)
  / busy (button labels swap to "Sending…" / "Verifying…").
- The phone block renders **only** when `NEXT_PUBLIC_AUTH_PHONE_OTP === "true"`; otherwise the page
  is byte-for-byte the S-002 page plus a one-word copy tweak.
- Watermark behavior: N/A (no preview / PDF in this slice).
- Components to reuse: the existing `/sign-in` form markup and `createClient()` auth-only client.
- No "Export JSON" / JSON editor added (standing rule — still true).

---

## Out of scope

- Account linking / merging (email sign-up + phone sign-up by the same human → two `sub`s). Deferred
  (roadmap).
- Deep-link-back / `next` param after login (kept as-is — every path funnels through `/auth/callback`,
  which always lands on `/` in v0 per ADR-004).
- Forced email capture for phone-only accounts; billing-receipt behaviour with a null email
  (billing slice).
- MSG91 API keys, DLT sender-ID registration — an ops task before the flag is turned on in prod.
- FastAPI sending the OTP itself — rejected in ADR-003; Supabase Auth owns the send.

---

## Dependencies

- S-001 (Accepted) — the JWT verifier + first-sight provisioning this slice extends.
- S-002 (Accepted) — the `/sign-in` page this slice conditionally extends.

---

## Definition of done (PM)

- [x] All AC verified in the test report ([`TR-S-005`](../test-reports/TR-S-005-phone-otp-login.md))
- [x] UX matches the notes above
- [x] `docs/roadmap.md` updated (SMS/phone OTP → `feature-flag`; account-linking row added); `mvp-spec.md` untouched
- [x] `README.md` auth paragraph + Wave/slice status table updated
- [x] `docs/architecture.md` AUTH OVERRIDE + `docs/architecture-sequences.md` sequence 1 updated (Architect)
- [x] PM `Status` set to **Accepted**

---

## Technical specification (Architect)

Checked against `docs/architecture-sequences.md` sequence 1 and `docs/ai-touchpoints.md`.

### API contract

| Method | Path | Auth | Request | Response | Errors |
|---|---|---|---|---|---|
| — | *(no new endpoint)* | — | — | — | — |
| GET | `/v1/me` | Bearer | — | `MeView` now includes `phone: str \| null` and `email: str \| null` | `401` unchanged; **new** `401` for a phone-only token while `AUTH_PHONE_OTP` is off, and for a token with no `email`/`phone` |

### Data model impact

- [ ] None  [x] Extend existing  [ ] New table(s) — Alembic migration: **yes** (`0002_user_phone`)
- `users.phone` — `String(32)`, nullable, indexed (`ix_users_phone`).
- `users.email` — altered `String(320)` **nullable** (was `NOT NULL`).
- Model: `User.email: Mapped[str | None]`, `User.phone: Mapped[str | None]`.

### Inference & money (cross-ref `docs/ai-touchpoints.md`)

- LLM call in this slice? **No.** Sign-in and JWT validation are already "No / No" rows; unchanged.
- Quota effect: none.
- Who sets prices: N/A (no pricing path touched).
- Failure behavior: fail-closed `401`, never `500` — consistent with ADR-001 §4.

### Side effects

- None. No PDF cache, no rate-limit change, no webhook, no storage. The SMS send + its rate limiting
  live in Supabase Auth.

### Frontend

- **Route(s):** `/sign-in`
- **Rendering:** client (unchanged — the page is already `"use client"`).
- **Components:** inline phone-entry + code-entry forms, gated by
  `process.env.NEXT_PUBLIC_AUTH_PHONE_OTP === "true"` read in the component body (testable).

### Flow

See `docs/architecture-sequences.md` sequence 1 — the new `else Phone OTP` branch and the
`else phone-only token while AUTH_PHONE_OTP is off → 401` alt.

### Architect checklist

- [x] API contract defined, `/v1`, matches the Wave 1 sequences (no new endpoint)
- [x] Data model impact documented; Alembic migration `0002`, never `create_all`
- [x] `docs/ai-touchpoints.md` still accurate — two AI hops, sign-in still zero-LLM
- [x] Money assembled by FastAPI before the model — N/A, untouched
- [x] `proposal_json` stays server-only — untouched
- [x] Supabase JWT verify only; `mock`/flag-off is the CI default
- [x] No secrets in the design (MSG91 keys live in Supabase, not this repo)

### Risks / tradeoffs

- Phone-only accounts have a null email — downstream features (follow-up email, billing receipts)
  must tolerate it. Flagged for the billing slice; not exercised in v0 while the flag is off.
- Two `sub`s for one human (email + phone) are not merged. Documented, deferred.
- The flag must be flipped in **three** places together (backend env, frontend env, Supabase SMS
  provider). The `.env.example` files and `docker-compose.yml` note this.

---

## Links

- Test plan: [`TP-S-005-phone-otp-login.md`](../test-plans/TP-S-005-phone-otp-login.md)
- Test report: [`TR-S-005-phone-otp-login.md`](../test-reports/TR-S-005-phone-otp-login.md)
- ADR: [`ADR-003-optional-phone-otp-login.md`](../adrs/ADR-003-optional-phone-otp-login.md)

---

## Changelog

| Date | Agent | Change |
|---|---|---|
| 2026-08-29 | PM | Created slice from the 2026-08-29 phone-OTP decision |
| 2026-08-29 | Architect | Tech spec — `users.phone` + nullable `email`, migration `0002`, flag gate, sequence 1 branch |
| 2026-08-29 | Builder | `config`/`deps`/`models`/`schemas`/`me` + `/sign-in` phone flow + env/compose |
| 2026-08-29 | Tester | 5 backend + 2 frontend tests; suite 66 BE / 14 FE green; migration up/down verified — see TR-S-005 |
| 2026-08-29 | PM | AC 1–8 verified; **Accepted** |
| 2026-08-29 | Verify | Split onto branch `s-005-phone-otp`; fixed un-flippable flag (`auth_phone_otp_enabled` → `auth_phone_otp`, env `AUTH_PHONE_OTP`); +2 backend tests (env binding, both-claims backfill); suite 68 BE / 14 FE |
| 2026-08-30 | Rebase | Rebased onto `main` after S-006 merged. `/sign-in` reconciled: phone-OTP success now hard-navigates to `/auth/callback` (same funnel as Google + email/password, ADR-004) instead of `router.push("/")`; `useRouter` dropped. `sign-in.test.tsx` merged with S-006's (`stubLocation` helper); phone test now also asserts the `/auth/callback` nav. §1 sequence diagram gained the phone branch alongside the S-006 callback branches. Suite 68 BE / 30 FE (6 sign-in). |
