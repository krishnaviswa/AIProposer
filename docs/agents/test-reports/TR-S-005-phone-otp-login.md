# TR-S-005: Phone OTP as an optional login method — Test report

| Field | Value |
|---|---|
| **Slice** | S-005 |
| **Author** | Tester |
| **Date** | 2026-08-29 |
| **Recommendation** | Ship |

---

## Summary

All 8 AC covered — 7 backend tests + 2 frontend tests added, migration `0002` verified up and down,
full suites green with no regressions. `docs/ai-touchpoints.md` is byte-identical to `main` (the two
v0 AI hops are untouched; sign-in stays a zero-LLM, zero-quota path). Default build and CI behaviour
is unchanged: no phone field, no SMS dependency, `email`-only accounts.

### Post-verification fix (2026-08-29, branch `s-005-phone-otp`)

A follow-up verification pass found the feature flag was **un-flippable via its documented switch**:
the setting field was `auth_phone_otp_enabled` (binds to env `AUTH_PHONE_OTP_ENABLED`), but
`.env.example` / `docker-compose.yml` set `AUTH_PHONE_OTP`, which `extra="ignore"` silently dropped.
Fixed: field renamed to `auth_phone_otp` (field name == env name, matching `ai_provider`/`AI_PROVIDER`);
`deps.py` updated; new regression test `test_auth_phone_otp_flag_binds_to_env_var`; new test
`test_phone_claim_backfilled_onto_email_account_even_when_flag_off` pins the both-claims backfill
behaviour. Backend suite now **68 passed**.

---

## AC coverage matrix

| AC# | Description | Type | Test reference | Result |
|---|---|---|---|---|
| 1 | Phone-only token → `401` when flag off | A | `test_auth_phone.py::test_phone_only_token_rejected_when_flag_off` | Pass |
| 2 | Phone-only token → provision phone-only account when flag on | A | `test_auth_phone.py::test_phone_only_token_provisions_account_when_flag_on` | Pass |
| 3 | `phone` backfilled onto an existing email account, no 2nd row | A | `test_auth_phone.py::test_phone_backfilled_onto_existing_email_account` | Pass |
| 4 | JWT with neither `email` nor `phone` → `401` | A | `test_auth_phone.py::test_token_with_neither_email_nor_phone_is_401` | Pass |
| 5 | Email + Google unchanged; `phone: null`; no phone field by default | A | `test_auth_phone.py::test_email_login_still_works_and_reports_no_phone` · `sign-in.test.tsx` (default) · 64 pre-existing tests | Pass |
| 6 | Flag on → `signInWithOtp` then `verifyOtp({type:"sms"})` → `/` | A | `sign-in.test.tsx::"shows the phone OTP flow when NEXT_PUBLIC_AUTH_PHONE_OTP=true"` | Pass |
| 7 | No `/v1` endpoint; no LLM / quota near sign-in | Review | `git diff main -- docs/ai-touchpoints.md` empty; no file added under `backend/app/routers/` | Pass |
| 8 | Migration `0002` adds `phone`, makes `email` nullable, reversible | A/M | `alembic upgrade head` + `downgrade base` on scratch sqlite; `PRAGMA table_info(users)` | Pass |

**Coverage:** 8 / 8 AC mapped

---

## Backend tests

### Added
- `backend/tests/test_auth_phone.py` — 7 tests (env-var binding, flag off/on, backfill ×2,
  no-identity, email regression)
- `backend/tests/conftest.py` — `make_token` gains `phone=` and only emits the claims it is given

### Run output
```
cd backend && python -m pytest -q
....................................................................     [100%]
68 passed in 12.92s
```
(61 pre-existing + 7 new. `test_auth.py` — email-token assertions — unchanged and green.)

---

## Frontend tests

### Added
- `frontend/src/app/__tests__/sign-in.test.tsx` — 2 tests (phone block hidden by default; full
  request-code → verify-code wiring when `NEXT_PUBLIC_AUTH_PHONE_OTP=true`)

### Run output
```
npm test
Test Suites: 5 passed, 5 total
Tests:       14 passed, 14 total
```
```
npx tsc --noEmit   # clean
npm run build      # green — /sign-in prerenders, 1.34 kB
```
(12 pre-existing + 2 new.)

---

## Migration verification

```
alembic -x url=sqlite:///./scratch.db upgrade head
  0001_initial -> 0002_user_phone
PRAGMA table_info(users) → email nullable (notnull=0), phone VARCHAR(32) present
alembic -x url=sqlite:///./scratch.db downgrade base   # 0002 -> 0001 -> base, clean
```

---

## Manual / integration

| ID | Check | Result |
|---|---|---|
| M-001 | Compose boots with `AUTH_PHONE_OTP` unset; email token → `phone: null` | Pass (settings default `false`; `test_email_login_still_works_and_reports_no_phone` is the automated proxy) |
| M-002 | `docs/ai-touchpoints.md` unchanged; no new `/v1` route | Pass |

---

## Regressions

None. All 61 backend + 12 frontend pre-existing tests pass unchanged. S-002's "sign-in has email +
Google, no OTP field" holds because the phone block is gated off by default.

---

## Gaps / rework items

None blocking. Noted for later (roadmap):
1. Phone-only accounts + a null email are not exercised against billing / follow-up-email — those
   paths are flag-off in v0.
2. Account linking (two `sub`s for one human) is out of scope by design.

---

## Sign-off

- [x] All AC mapped to tests (A or M)
- [x] Auth (`401`) tested — flag-off gate, no-identity, plus existing invalid-JWT suite
- [x] Ownership (`404`) — N/A, no owned-resource path touched
- [x] Money invariant — N/A, no pricing path touched
- [x] `docs/ai-touchpoints.md` still matches the code (empty diff)
- [x] Ready for PM acceptance
