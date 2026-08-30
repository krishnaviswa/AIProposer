# TP-S-005: Phone OTP as an optional login method — Test plan

| Field | Value |
|---|---|
| **Slice** | S-005 |
| **Author** | Tester |
| **Date** | 2026-08-29 |

---

## Scope

The `phone` identity claim path in `get_current_user`, the `AUTH_PHONE_OTP` feature-flag gate, the
`users.phone` column + nullable `email` (model + migration `0002`), `MeView.phone`, and the
flag-gated phone flow on `/sign-in`. The SMS send itself is Supabase Auth's and is **not** under
test — the client calls are mocked.

---

## Test strategy

| Layer | Tool | Focus |
|---|---|---|
| Backend API | pytest | flag-off rejection (`401`), flag-on provisioning, phone backfill, no-identity `401`, email path unchanged |
| Frontend | Jest + RTL | phone block hidden by default; `signInWithOtp` → `verifyOtp` wiring when the flag is on |
| Migration | alembic | `upgrade head` and `downgrade base` on sqlite + inspection of `users` columns |
| Integration | manual | `docker compose up --build` boots with `AUTH_PHONE_OTP` unset (default off) |

Environment: `AI_PROVIDER=mock`, `PAYMENTS_PROVIDER=mock`, `STORAGE=local`, `EMAIL_PROVIDER=mock`,
`AUTH_PHONE_OTP` unset. No live vendors, no Supabase network.

---

## AC → planned tests

| AC# | Test approach | Test ID / file |
|---|---|---|
| 1 | Automated | `backend/tests/test_auth_phone.py::test_phone_only_token_rejected_when_flag_off` |
| 2 | Automated | `backend/tests/test_auth_phone.py::test_phone_only_token_provisions_account_when_flag_on` |
| 3 | Automated | `backend/tests/test_auth_phone.py::test_phone_backfilled_onto_existing_email_account` |
| 4 | Automated | `backend/tests/test_auth_phone.py::test_token_with_neither_email_nor_phone_is_401` |
| 5 | Automated | `backend/tests/test_auth_phone.py::test_email_login_still_works_and_reports_no_phone` · `frontend/src/app/__tests__/sign-in.test.tsx` ("hides the phone option by default") · full existing suites as regression |
| 6 | Automated | `frontend/src/app/__tests__/sign-in.test.tsx` ("shows the phone OTP flow when …=true") |
| 7 | Review | `docs/ai-touchpoints.md` diff = empty; no route added under `backend/app/routers/` |
| 8 | Automated + manual | `alembic upgrade head` / `downgrade base` on a scratch sqlite db; `PRAGMA table_info(users)` |

---

## Standing-invariant cases

| Case | Expected |
|---|---|
| No / invalid JWT | `401` (existing `test_auth.py`, must still pass) |
| Valid email JWT | unchanged `200`, `phone: null` |
| Money / quota / PATCH / webhook | untouched by this slice — full suite is the regression gate |

---

## Edge cases

- Token carrying both `email` and `phone` → account has both; no gate trip.
- `phone` claim present but empty string → treated as absent (`claims.get("phone") or None`).
- Flag toggled per-test via `monkeypatch.setattr(get_settings(), "auth_phone_otp", True)`; a
  separate test asserts `AUTH_PHONE_OTP` (env) binds to `Settings.auth_phone_otp`.

---

## Manual checklist

- [ ] M-001: `docker compose up --build` — backend boots, `GET /v1/me` with an email token returns
  `phone: null`, no `AUTH_PHONE_OTP` set.
- [ ] M-002: `docs/ai-touchpoints.md` unchanged; grep confirms no new `/v1` route.

---

## Environment notes

- Tests build the schema with `Base.metadata.create_all` (not migrations), so migration `0002` is
  exercised separately with an explicit `alembic` run.
