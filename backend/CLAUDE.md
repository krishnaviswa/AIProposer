# Backend rules (FastAPI)

> Mirrors `.cursor/rules/backend-fastapi.mdc` (Cursor `globs: backend/**/*`), plus the backend half
> of `.cursor/rules/testing.mdc`. Keep in sync — see the parity table in the root
> [`CLAUDE.md`](../CLAUDE.md).

> No backend code exists yet — Wave 3 (Phase 1) creates it. This file is the standing contract for
> when it does. `app/services/ai/` and `app/services/payments|storage|email/` gain their own nested
> `CLAUDE.md` in Wave 3 when the adapter code lands (add the new pairs to `SYNC_GROUPS` then).

## Layering

- `app/routers/` — HTTP only: schemas, JWT dependency, status codes. No business logic.
- `app/services/` — quota, pricing assembler, generation, PDF, billing.
- `app/services/ai/`, `payments/`, `storage/`, `email/` — adapter packages: `mock` + one real impl each,
  `TokenUsage` + `estimated_cost_usd` on every AI call, startup validation of missing keys.
- `app/models/` — SQLAlchemy ORM, tables per `mvp-spec.md` §6.
- `app/schemas/` — Pydantic DTOs, including the proposal **view DTO** (not `proposal_json`).
- `app/deps.py` — `current_user` (verify Supabase JWT via JWKS → `sub`), ownership guard.

## Hard rules (`mvp-spec.md` + Wave 1 docs)

1. Base path `/v1`. Static routes before dynamic.
2. **JWT verify only** — signature + `exp` + `aud` against Supabase JWKS. No passlib, no token issuing.
3. **Pricing assembler runs before the model** on generate/regenerate; egress strips/overwrites any
   `pricing[].amount` from the model with server values (`docs/ai-touchpoints.md`).
4. LLM is called **only** from the generation service, only on `POST /v1/proposals` and
   `POST /v1/proposals/{id}/regenerate`. `PATCH`, PDF, list/detail, duplicate, billing → no model call.
5. Quota: `UsageRecords.proposals_count` +1 **only after** a valid `proposal_json` is saved.
   Parse/validate fail → `502`, 0 quota, nothing persisted. Max 1 automatic retry.
6. `PATCH /v1/proposals/{id}` — allowlisted keys only (else `422`). Price edits are plain writes.
   Any successful PATCH nulls `pdf_url`.
7. `GET` list/detail return the **view DTO**. Never serialize raw `proposal_json`.
8. Rate limit `POST /v1/proposals` (per user + per IP); max 1 concurrent LLM call per user.
9. Billing webhook: HMAC via `hmac.compare_digest`; upsert `WebhookEvents` on unique
   `provider_event_id`; duplicate → `200` no-op.
10. Storage: private objects, signed short-TTL URLs only.

## New endpoint checklist

1. Request + response schema in `app/schemas/`.
2. Router function with docstring (method, auth, request, response, errors); logic in a service.
3. Auth / ownership via `app/deps.py`.
4. Alembic migration if the schema changed (never `create_all`).
5. Pytest in `backend/tests/` (happy path + `401` + ownership `404`), `AI_PROVIDER=mock`.
6. Architect updates `docs/architecture-sequences.md` / `docs/ai-touchpoints.md` if the flow changed.

## Errors

`HTTPException` with `400/401/403/404/409/422/429/502`. Never leak stack traces or the system prompt.

## Testing

> Mirrors `.cursor/rules/testing.mdc` (backend half). Keep in sync.

- **No live vendors.** `AI_PROVIDER=mock`, `PAYMENT_PROVIDER=mock`, `STORAGE=local`,
  `EMAIL_PROVIDER=mock`. JWTs verified against a test JWKS / fake, no Supabase network.
- `httpx.AsyncClient` + `ASGITransport` against `app.main:app`.
- Per endpoint: happy path, `401` unauthenticated, `404` on another user's row.
- Generation tests (mock AI adapter) assert: saved prices == user's saved amounts; a model-emitted
  amount is overwritten; quota +1 only on saved success; parse-fail → +0.
- Billing tests: HMAC reject on bad signature; duplicate `provider_event_id` is a no-op.
- Default run: only the files for the area changed. Full `pytest` before merge / shared helper / when asked.
