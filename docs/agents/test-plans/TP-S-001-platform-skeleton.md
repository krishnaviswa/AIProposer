# TP-S-001: Platform skeleton — Test plan

| Field | Value |
|---|---|
| **Slice** | S-001 |
| **Author** | Tester |
| **Date** | 2026-08-29 |

---

## Scope

The FastAPI `/v1` skeleton: JWT verification, `/v1/me` profile + packages, proposals CRUD, PATCH
allowlist, quota counter, generate/regenerate/duplicate against the **mock** AI adapter, PDF stub,
and the billing checkout + webhook stub. No frontend.

---

## Test strategy

| Layer | Tool | Focus |
|---|---|---|
| API | pytest + httpx `ASGITransport` | real dependency chain, real JWT verify (HS256 dev secret) |
| DB | in-memory aiosqlite per test, `Base.metadata.create_all`, plan catalog seeded | isolation, no Postgres needed |
| Verifier | pytest unit | HS256 + RS256 (local keypair as fake JWKS) + missing-`sub` |
| Migration | `python -m alembic upgrade head` on SQLite + Postgres (CI) | schema matches models |

Environment: `SUPABASE_JWT_ALG=HS256`, `AI_PROVIDER=mock`, `PAYMENTS_PROVIDER=mock`,
`STORAGE_PROVIDER=local`, `EMAIL_PROVIDER=mock`. No network.

Mock sentinels used: `__FAIL__` (force `AIGenerationError`), `__MODEL_TRIES_PRICE__` (mock emits an
amount the server must strip).

---

## AC → planned tests

| AC# | Area | Test file |
|---|---|---|
| 1–3 | auth: 401 no/invalid token, first-use provisioning | `test_auth.py` |
| 4–5 | `PUT /v1/me` persist + validation | `test_me.py` |
| 6–10 | generate: server prices, price-strip, 502/0-quota, 402, hourly math | `test_proposals_generate.py` |
| 11–13, 15–16 | list/detail ownership, PATCH allowlist, duplicate, pdf stub | `test_proposals_crud.py` |
| 14 | regenerate re-derives prices, nulls pdf, quota, failure keeps copy | `test_regenerate.py` |
| 17–19 | checkout stub, webhook HMAC + idempotency + anchor, bad-sig 400 | `test_billing.py` |
| 20–21 | rate-limit 429, only-mock-AI, non-mock fails boot | `test_rate_limit_and_startup.py` |
| — | health, root, lifespan validate | `test_health.py` |

---

## Standing-invariant cases (all covered)

| Case | Expected | Test |
|---|---|---|
| No / invalid / expired / wrong-aud / wrong-sig JWT | 401 | `test_auth.py` |
| Another user's proposal (GET/PATCH/pdf/regenerate) | 404 | `test_proposals_crud.py` |
| Model returns a price | server overwrites; saved == user's | `test_proposals_generate.py::test_model_supplied_price_is_discarded` |
| Generate parse-fail | 502, quota +0, no row | `test_proposals_generate.py::test_generation_failure_is_502_with_no_quota_and_no_row` |
| Non-allowlisted PATCH key | 422 | `test_proposals_crud.py::test_patch_unknown_key_is_422` |
| Duplicate webhook `provider_event_id` | 200 no-op | `test_billing.py::test_webhook_upgrades_plan_and_is_idempotent` |
| No `proposal_json` in any response | asserted on list + detail | `test_proposals_*` |

---

## Manual / integration checklist

- [ ] M-001: `python -m alembic upgrade head` on a fresh SQLite file, then `scripts/seed.py` → `plans` has `free`(3) + `starter_inr`(20)
- [ ] M-002: `lifespan(app)` context enters without raising on the default mock config
- [ ] M-003: `compileall` clean across `app/ scripts/ tests/`
