# ADR-004: Auth redirect landing via a single `/auth/callback` route

| Field | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-08-29 |
| **Slice** | S-006 |

---

## Context

`mvp-spec.md` §3.1 / §13.1 and the AUTH OVERRIDE in [`architecture.md`](../../architecture.md) fix v0
auth as **Supabase Auth — email/password (verified) + Google OAuth**, with FastAPI *only* verifying
the JWT. [`architecture-sequences.md`](../../architecture-sequences.md) §1 shows the browser getting a
session from Supabase and then calling `/v1` with the bearer token.

S-002 shipped the client but took two shortcuts that only surface with a real Supabase project:

- **Google OAuth had nowhere to land.** `signInWithOAuth` used `redirectTo = <origin>/`, so Supabase
  redirected to `/` with a PKCE `?code=...` in the URL and nothing ever exchanged it for a session.
- **Email/password and email-verification links** each did their own ad-hoc `router.push("/")`.

The PKCE `code` → session exchange has to happen somewhere. `@supabase/ssr` stores the PKCE code
verifier in a **cookie**, so either the browser client or a server route handler can complete it.
CLAUDE.md non-negotiable #5 ("never business logic in a Next.js route handler") is in play, as is the
frozen "one auth path, Supabase JWT verify only" rule (#6).

Two product questions were resolved by the user for S-006:

1. **No `next` / `redirectTo` deep-link support in v0** — always land on `/`.
2. **Every** post-auth landing (Google, email verify, *and* the existing email/password sign-in) is
   routed through one place.

---

## Decision

1. **One landing route: `GET /auth/callback`**, implemented as a Next.js **route handler**
   (`frontend/src/app/auth/callback/route.ts`). It is *not* a page — no UI, no data fetch.
2. **It does exactly two things:** (a) a Supabase Auth session operation via `@supabase/ssr`
   `createServerClient` — `exchangeCodeForSession(code)` when a `?code=` is present — and (b) an
   HTTP redirect. No `/v1` call. No pricing, quota, proposal, or any domain logic. This is an
   auth-session operation (the same category as `signInWithPassword`), which
   [`frontend/CLAUDE.md`](../../../frontend/CLAUDE.md) already permits the Supabase client to do; it is
   **not** the "business logic" #5 forbids. FastAPI remains the only JWT verifier and the only holder
   of business logic.
3. **Redirect targets (v0, fixed — no param parsing):**
   - `?error=...` present, **or** the code exchange throws → `303` to `/sign-in?error=<message>`, no
     session set.
   - `?code=...` exchanged OK → `303` to `/`.
   - No `?code=` and a valid session already on the request (the email/password path) → `303` to `/`.
   - No `?code=` and no session → `303` to `/sign-in`.
4. **All three entry points funnel here:**
   - Google: `signInWithOAuth({ options: { redirectTo: `${origin}/auth/callback` } })`.
   - Email verification / magic links: Supabase "Site URL" + redirect allow-list point at
     `/auth/callback` (config, not code).
   - Email/password: on `signInWithPassword` success the page does a **hard navigation**
     (`window.location.assign("/auth/callback")`) so the route handler actually runs.
5. **`/auth` stays in the middleware `PUBLIC_PATHS`** (already true) so the callback is reachable
   pre-session.
6. **No `next` / `redirectTo` / deep-link-back.** A future open-redirect-guarded same-origin variant
   is a roadmap item, not v0.

---

## Consequences

### Positive

- One code path for every sign-in outcome; the OAuth `code` is actually exchanged.
- Server-side cookie set on the redirect response — no client-side token flash, no "logged in but
  middleware still 302s you" race.
- The route handler is trivially unit-testable offline (import `GET`, pass a mock `Request`, mock
  `createServerClient`) — satisfies the S-006 CI constraint.
- Nothing about the FastAPI JWT-verify contract changes; `architecture-sequences.md` §1 only gains a
  hop, it does not change trust boundaries.

### Negative / tradeoffs

- A route handler that touches the Supabase SDK sits close to the #5 line. Mitigated by keeping it to
  code-exchange + redirect and asserting "no `/v1` call, no domain logic" in the S-006 checklist.
- The email/password path now costs one extra full navigation (`/sign-in` → `/auth/callback` → `/`).
  Acceptable; it removes a second bespoke redirect.
- The PKCE verifier must survive the round-trip as a cookie (it does with `@supabase/ssr`); a
  cookie-blocked browser would fail the exchange and land on `/sign-in?error=...` — correct behavior.

### Follow-ups

- Wave 1 docs to update: [`architecture-sequences.md`](../../architecture-sequences.md) **§1** — add
  the `/auth/callback` code-exchange hop for both branches; keep the "No LLM. No quota." note.
  `architecture.md` and `ai-touchpoints.md` unchanged (no container, boundary, LLM, or quota change).
- `docs/roadmap.md`: add "deep-link-back-after-login (open-redirect-guarded same-origin `next`)".

---

## Alternatives considered

1. **Client page (`app/auth/callback/page.tsx`, `"use client"`) that calls
   `exchangeCodeForSession` from the browser client**, then `router.replace("/")`. Works and is
   arguably further from the #5 line, but re-introduces a token flash and a session/middleware race,
   and still needs the hard-nav for the email/password case. Rejected in favour of the documented
   `@supabase/ssr` server pattern.
2. **Keep per-entry-point redirects, only add a callback for Google.** Leaves two code paths and the
   email-verification link still landing somewhere ad hoc. Rejected — the user asked for one funnel.
3. **Support a same-origin `next` param now.** More flexible, but every `next`/`redirectTo` param is
   an open-redirect footgun and the deep-link need is hypothetical in v0. Deferred to roadmap.
