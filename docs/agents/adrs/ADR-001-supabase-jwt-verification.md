# ADR-001: Supabase JWT verification in FastAPI

| Field | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-08-29 |
| **Slice** | S-001 |

---

## Context

`mvp-spec.md` §0.2, §6, §8, §18.2 and `docs/architecture.md` fix identity as **Supabase Auth**, with
FastAPI **only verifying** the JWT — no `password_hash`, no passlib, no token issuing. The MEngPlat
pattern repo ships a custom HS256 + passlib auth stack that is explicitly *not* to be copied
(`mvp-spec.md` §18.2). Wave 3 needs a concrete verification mechanism.

Supabase issues access tokens two ways depending on project age / settings:

- **HS256** with the project's JWT secret (symmetric shared secret) — the long-standing default.
- **RS256 / ES256** with rotating signing keys published at
  `https://<ref>.supabase.co/auth/v1/.well-known/jwks.json` — the newer asymmetric-keys feature.

`docs/architecture.md` sequence 1 already says "verify signature + exp + aud against Supabase JWKS".

---

## Decision

1. **Library: `PyJWT[crypto]`** (+ `httpx` for the JWKS fetch). Not `python-jose` (less maintained,
   CVE history) and not a hand-rolled verifier.
2. **Support both algorithms, selected by `SUPABASE_JWT_ALG`:**
   - `RS256` (default for real deploys): `jwt.PyJWKClient(SUPABASE_JWKS_URL)` with a cached key set;
     verify `signature`, `exp`, and `aud` (`SUPABASE_JWT_AUD`, default `"authenticated"`).
   - `HS256` (default for local dev + tests): verify with `SUPABASE_JWT_SECRET`. No network.
3. **`sub` (a UUID) is the user id.** `get_current_user` **upserts** a `users` row the first time a
   `sub` is seen (email from the `email` claim), then returns it. There is no `/register` endpoint —
   Supabase owns sign-up.
4. **Fail closed.** A missing/invalid token, a JWKS fetch failure, or an inactive user → `401`,
   never `500`, never a fallback to an unauthenticated identity.
5. **The only authorization rule is ownership.** `require_owner` returns `404` (not `403`) when a row's
   `user_id` != the caller — there are no roles in v0.

---

## Consequences

### Positive

- Matches the spec (no custom auth) and `docs/architecture.md` sequence 1 exactly.
- Tests need no network: they override `get_current_user`, and unit-test the verifier with a locally
  generated RSA keypair served as a fake JWKS and with an HS256 secret.
- Swapping a Supabase project = three env vars, no code change.

### Negative / tradeoffs

- Two code paths to maintain (HS256 + RS256). Kept small — one `verify_jwt(token) -> claims` function.
- JWKS is fetched over the network in the RS256 path; mitigated by an in-process cached client with a
  TTL and a fail-closed `401` on fetch error.
- First-use row provisioning means a valid JWT for a deleted Supabase user would re-create a local
  row. Acceptable for v0; a Supabase "user deleted" webhook is roadmap work.

### Follow-ups

- Wave 1 docs: none needed — sequence 1 already describes JWKS verification.
- `docs/roadmap.md`: add "Supabase user-deletion sync" as a deferred item.

---

## Alternatives considered

1. **HS256 only.** Simpler, but contradicts the architecture doc and the direction Supabase is moving
   (asymmetric keys). Rejected as the sole path; kept as the dev/test path.
2. **`python-jose`** (matches MEngPlat's dependency). Rejected — maintenance + CVE history; PyJWT has
   first-class JWKS support via `PyJWKClient`.
3. **Supabase `/auth/v1/user` introspection call per request.** A network round-trip on every API
   call. Rejected — local signature verification is the point of a JWT.
