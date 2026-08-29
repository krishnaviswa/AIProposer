# ADR-003: Phone OTP as an optional, feature-flagged Supabase Auth method

| Field | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-08-29 |
| **Slice** | S-005 |

---

## Context

The frozen `mvp-spec.md` (§3.1, §13.1, §18.2, §460) ships v0 auth as **verified email + Google
only** and lists "phone OTP / MSG91" as out of scope. `docs/roadmap.md` tracked the India +91 SMS
rail as `blocked-on-decision`, and `docs/architecture.md` recorded the AUTH OVERRIDE fallback.

On 2026-08-29 the product owner decided to **add phone OTP as an optional sign-in method** —
alternative sign-in (phone-only accounts allowed), MSG91 as the production SMS provider for the +91
rail, and no edit to the frozen spec (it moves to a `feature-flag` roadmap entry instead).

ADR-001 already fixes the identity contract: FastAPI **only verifies** the Supabase JWT and provisions
a local `users` row on first sight of a `sub`. Supabase Auth owns sign-up and the SMS send.

---

## Decision

1. **The SMS send stays entirely in Supabase Auth.** `supabase.auth.signInWithOtp({ phone })` +
   `verifyOtp(...)` on the client; the SMS provider (MSG91 for +91) is configured in the Supabase
   dashboard. FastAPI gains **no** SMS dependency and **no** new endpoint — the JWT-verification
   contract is unchanged. `docs/ai-touchpoints.md` is unchanged: login is still a zero-LLM path.
2. **Two feature flags, both default `false` and `false` in CI:**
   - Backend `AUTH_PHONE_OTP` (`Settings.auth_phone_otp` — field name == env name).
   - Frontend `NEXT_PUBLIC_AUTH_PHONE_OTP` (renders the phone option on `/sign-in`).
3. **Identity claims.** `get_current_user` reads `email` and `phone` from the verified claims.
   `users.email` becomes **nullable**; `users.phone` is added (nullable, indexed). One of the two is
   always set.
4. **Flag-off is a hard gate.** With `AUTH_PHONE_OTP` false, a phone-only token (a `phone` claim and
   no `email`) is rejected `401` — enabling phone accounts is a deliberate switch, not a silent
   consequence of someone obtaining a phone token. A token with neither claim is also `401`.
5. **Phone-only accounts are first-class.** No forced email capture in v0. A `phone` seen later on an
   existing account is backfilled onto that row.

---

## Consequences

### Positive

- Frozen spec untouched; the change is a roadmap `feature-flag` row + this ADR.
- Default build and CI behaviour is identical to before — email + Google, no phone field, no SMS
  cost, S-002's "no OTP field" parity assertion still holds.
- Backend delta is small: one setting, one nullable column + one new column, a short branch in
  `get_current_user`, and `MeView` gains `phone`.

### Negative / tradeoffs

- Phone-only accounts have no verified email — billing receipts and the follow-up-email feature must
  tolerate a null email (out of scope for S-005; noted for the billing slice).
- DLT sender-ID registration is required for +91 SMS via MSG91 — an ops task before the flag is
  turned on in production.
- Account-linking (same person, separate email and phone sign-ups → two `sub`s → two rows) is **not**
  solved here; deferred (roadmap).

### Follow-ups

- `docs/roadmap.md`: SMS / phone OTP row → `feature-flag`; add "phone/email account linking" as
  `deferred`.
- `docs/architecture.md` AUTH OVERRIDE + `docs/architecture-sequences.md` sequence 1: add the phone
  branch (behind the flag).

---

## Alternatives considered

1. **Amend the frozen spec.** Rejected — the owner chose the feature-flag route; keeps the freeze
   meaningful and lets the flag ship dark until MSG91 + DLT are ready.
2. **Add-on only (every account must have a verified email first).** Rejected — the owner chose
   alternative sign-in with phone-only accounts allowed.
3. **FastAPI sends the OTP itself (MSG91 API + a `/v1/auth/otp` endpoint).** Rejected — duplicates
   what Supabase Auth already does, adds a secret and a rate-limit surface to FastAPI, and breaks the
   ADR-001 "verify only, never issue" contract.
