# TR-S-001: Platform skeleton — Test report

| Field | Value |
|---|---|
| **Slice** | S-001 |
| **Author** | Tester |
| **Date** | 2026-08-29 |
| **Recommendation** | **Ship** |

---

## Summary

**42 pytest tests pass** (`PYTHONPATH=. python -m pytest -q` → `42 passed`). All 21 acceptance
criteria are mapped and green. JWT verification (HS256 + RS256), first-use user provisioning, profile
+ packages, proposals CRUD, the PATCH allowlist, the quota counter, generate/regenerate/duplicate
against the mock adapter, the money invariant (server prices win, model amounts stripped), the
0-quota failure path, the PDF stub, and the billing checkout + HMAC webhook + idempotency all behave
as specified. `docs/ai-touchpoints.md` is unchanged — Wave 3 has **zero production AI hops** and
`AI_PROVIDER != mock` fails at boot.

---

## AC coverage matrix

| AC# | Description | Type | Test reference | Result |
|---|---|---|---|---|
| 1 | No token → 401 on protected routes | A | `test_auth.py::test_no_token_is_401` | Pass |
| 2 | Invalid / expired / wrong-aud / wrong-sig → 401 | A | `test_auth.py::test_garbage_token_is_401`, `test_expired_token_is_401`, `test_wrong_audience_is_401`, `test_wrong_signature_is_401` | Pass |
| 3 | Valid JWT, unknown sub → provision row, plan=free | A | `test_auth.py::test_valid_token_provisions_user_with_free_plan` | Pass |
| 4 | `PUT /v1/me` persists profile + packages; `GET` returns plan+usage | A | `test_me.py::test_put_me_persists_profile_and_packages` | Pass |
| 5 | Bad currency / non-int amount / >3 packages → 422 | A | `test_me.py::test_put_me_rejects_bad_currency`, `_non_integer_amount`, `_more_than_three_packages` | Pass |
| 6 | Generate: saved `pricing` == user's amounts; usage +1; DTO not `proposal_json` | A | `test_proposals_generate.py::test_generate_uses_server_prices_and_returns_dto` | Pass |
| 7 | Model-supplied price discarded | A | `test_proposals_generate.py::test_model_supplied_price_is_discarded` | Pass |
| 8 | `__FAIL__` → 502, usage unchanged, no row persisted | A | `test_proposals_generate.py::test_generation_failure_is_502_with_no_quota_and_no_row` | Pass |
| 9 | At limit → 402 upgrade hint, no model call, usage unchanged | A | `test_proposals_generate.py::test_over_quota_is_402_no_model_call` | Pass |
| 10 | Hourly: amount = rate × hours, server-side | A | `test_proposals_generate.py::test_hourly_mode_amount_is_rate_times_hours` (+ `_without_saved_rate_is_422`, `_fixed_mode_uses_user_typed_amount`) | Pass |
| 11 | List/detail owner-scoped; other user's id → 404; no `proposal_json` | A | `test_proposals_crud.py::test_list_and_detail_are_owner_scoped` | Pass |
| 12 | PATCH allowlisted field updates, nulls pdf_url, no quota, no model | A | `test_proposals_crud.py::test_patch_allowlisted_field_updates_and_nulls_pdf` | Pass |
| 13 | Non-allowlisted key (`proposal_json`, `user_id`, `llm_output_tokens`, `pdf_url`) → 422 | A | `test_proposals_crud.py::test_patch_unknown_key_is_422` | Pass |
| 14 | Regenerate re-derives prices from current saved amounts, nulls pdf, usage +1; failure keeps old copy + counter; over-quota → 402 | A | `test_regenerate.py::test_regenerate_tracks_current_saved_package_amount`, `_over_quota_is_402`, `_failure_keeps_old_copy_and_quota` | Pass |
| 15 | Duplicate clones inputs + last JSON, no model call, no quota | A | `test_proposals_crud.py::test_duplicate_clones_without_model_call_or_quota` | Pass |
| 16 | `GET .../pdf` → 501 stub, no model, no quota | A | `test_proposals_crud.py::test_pdf_is_stubbed` | Pass |
| 17 | Checkout session → order params (paise), no plan change | A | `test_billing.py::test_checkout_session_returns_order_params_no_plan_change` (+ `_rejects_unknown_or_free_plan`) | Pass |
| 18 | Valid webhook → plan `starter_inr`, subscription row, period re-anchored (`included`→20); replay → 200 no-op | A | `test_billing.py::test_webhook_upgrades_plan_and_is_idempotent` | Pass |
| 19 | Bad HMAC → 400, no state change | A | `test_billing.py::test_webhook_bad_signature_is_400_no_change` | Pass |
| 20 | Exceed rate on `POST /v1/proposals` → 429, quota unaffected by rejects | A | `test_rate_limit_and_startup.py::test_generate_is_rate_limited` | Pass |
| 21 | Only `MockAIProvider` wired; `AI_PROVIDER != mock` fails boot with "Wave 4" | A | `test_rate_limit_and_startup.py::test_only_mock_ai_is_registered`, `test_non_mock_ai_provider_fails_startup` | Pass |

**Coverage:** 21 / 21 AC mapped, all Pass.

---

## Backend tests

### Added (42 tests across 8 files)

`tests/test_auth.py` (11), `tests/test_me.py` (4), `tests/test_proposals_generate.py` (8),
`tests/test_proposals_crud.py` (6), `tests/test_regenerate.py` (3), `tests/test_billing.py` (4),
`tests/test_rate_limit_and_startup.py` (3), `tests/test_health.py` (3).
Harness: `tests/conftest.py` (aiosqlite per test, real app, real HS256 verify, limiter reset),
`tests/helpers.py`.

### Run output

```
$ cd backend && PYTHONPATH=. python -m pytest -q
..........................................                               [100%]
42 passed in ~13s
```

---

## Frontend tests

None — the Next.js client is slice S-002.

---

## Manual / integration

| ID | Check | Result |
|---|---|---|
| M-001 | `alembic upgrade head` (SQLite) + `scripts/seed.py` → `plans` = free(3), starter_inr(20) | Pass |
| M-002 | `async with lifespan(app)` on default mock config | Pass — "lifespan startup OK" |
| M-003 | `python -m compileall app scripts tests` | Pass |

CI: `.github/workflows/backend-tests.yml` runs the same suite against a Postgres service container
on `pull_request` (paths `backend/**`). No live keys anywhere.

---

## Regressions

None. Wave 1/2 docs and config are untouched except: a build note added to
`docs/architecture-sequences.md` (not a SYNC_GROUP file), `README.md` status table, `docs/roadmap.md`
(two new deferred rows), and the S-001 slice/ADR/TP/TR artifacts.

---

## Gaps / rework items (non-blocking)

1. **`backend/CLAUDE.md` + `frontend/CLAUDE.md` still say "no code exists yet".** Left stale on
   purpose this commit — updating `backend/CLAUDE.md` drags in `testing.mdc` + `frontend/CLAUDE.md`
   via SYNC_GROUPS. Fix in a dedicated parity-sync commit that touches all of them together.
2. **Per-user single-flight lock is in-process only** (`asyncio.Lock` per user id). Fine for the
   single-instance v0 deploy; a distributed lock is Wave 4. Recorded in `docs/roadmap.md`.
3. **Regenerate for `packages` mode depends on stable package ids.** `PUT /v1/me` now upserts by
   label to keep ids stable; if a user renames a package, a proposal built on the old label will
   `422` on regenerate (clear message). Acceptable for v0.
4. **`_ingress_flags` is stored inside `proposal_json`** but not surfaced in the DTO. Intentional —
   it's operational metadata, not user copy.

---

## Sign-off

- [x] All 21 AC mapped to automated tests
- [x] Auth (401) and ownership (404) tested on every protected route
- [x] Money invariant tested (server assembles, model amount stripped, regenerate re-derives)
- [x] `docs/ai-touchpoints.md` still matches the code — zero production AI hops in Wave 3
- [x] Ready for PM acceptance
