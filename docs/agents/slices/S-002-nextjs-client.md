# Slice: S-002 — Next.js web client

| Field | Value |
|---|---|
| **Slice ID** | S-002 |
| **Phase** | 1 Platform skeleton |
| **Status** | Accepted |
| **Owner** | PM / 2026-08-29 |

> **Wave 3, second half.** The browser client for the `S-001` API. Talks **only** to FastAPI `/v1`.
> Supabase for the auth session; every data operation goes through `src/lib/api.ts`. Split
> preview + section forms, **no JSON export**, watermark on Free. No new backend behaviour.

---

## User story

**As a** freelancer
**I want** to sign in, set my rates, and create + edit proposals in a browser
**So that** I can actually use the workflow the API already supports

---

## Acceptance criteria

1. **Given** I am not signed in, **when** I open any route except `/sign-in`, **then** the
   middleware redirects me to `/sign-in`.
2. **Given** the sign-in page, **when** I submit email + password or click "Continue with Google",
   **then** Supabase auth runs and, on success, I land on the dashboard. (No SMS, no TOTP.)
3. **Given** any API call from the client, **when** it is made, **then** it goes to
   `NEXT_PUBLIC_API_BASE_URL` (FastAPI `/v1`) with `Authorization: Bearer <supabase access token>`
   and to **no other host**.
4. **Given** the settings page, **when** I save a name, quote currency, hourly rate, and 1–3
   packages, **then** `PUT /v1/me` is called and the form reflects the saved values; a bad amount is
   caught client-side before the request.
5. **Given** the new-proposal form, **when** I fill a brief + pick `packages` / `hourly` / `fixed`
   pricing and click Generate, **then** `POST /v1/proposals` is called and I am taken to the editor;
   a `402` shows a plan-limit message.
6. **Given** the editor, **when** it renders, **then** the left pane is a **PDF-like preview** of the
   view DTO and the right rail is **section forms** bound to the same fields. There is **no JSON
   view, no "Export JSON", no "Copy source"** control anywhere.
7. **Given** the editor, **when** I edit a section field (summary / scope / terms / follow-up) and
   blur, **then** `PATCH /v1/proposals/{id}` is called with a `sections.*` allowlist body.
8. **Given** the editor, **when** I change a **price** field and blur, **then** `PATCH` is called
   with a `pricing` body — **not** a regenerate; the AI is not re-run.
9. **Given** a Free-plan user, **when** the editor renders, **then** the preview carries a
   "NOT FOR SENDING" watermark and the follow-up email is hidden; a paid plan renders clean.
10. **Given** the editor, **when** I click Regenerate / Duplicate, **then** the matching
    `POST /v1/proposals/{id}/regenerate|duplicate` is called; "Download PDF" shows a
    "arrives in Wave 4" note (the API returns `501`).
11. **Given** the repo, **when** CI runs, **then** `typecheck` + `jest` + `next build` all pass with
    no backend and no real Supabase project.

---

## UX notes

- Routes: `/sign-in`, `/` (dashboard list), `/settings`, `/proposals/new`, `/proposals/[id]` (editor).
- States handled: loading, empty (no proposals), error (load failed), `402` on generate/regenerate.
- Free-plan watermark: banner + diagonal overlay on the preview + `select-none`.
- Tailwind, minimal styling — this is a skeleton, not the finished landing/marketing UI.

---

## Out of scope

- Landing / marketing page, FAQ, INR/USD toggle (later).
- Real PDF download, WhatsApp share link, follow-up-email copy button (Wave 4).
- SSR of the preview / dashboard (currently client components + hooks) — see roadmap.
- Razorpay checkout UI beyond the `checkout-session` call (Wave 4).
- Mobile-perfect layout, dark mode, design system.

---

## Dependencies

- `S-001` platform skeleton — Accepted (`2c31e19`).

---

## Definition of done (PM)

- [x] All 11 AC verified in the test report
- [x] Client talks only to FastAPI `/v1` (asserted in `api.test.ts`)
- [x] No "Export JSON" / JSON view anywhere (asserted in `PreviewPane.test.tsx`)
- [x] Price edit → PATCH not regenerate (asserted in `SectionForms.test.tsx`)
- [x] `typecheck` + `jest` (8 tests) + `next build` green; `frontend-tests.yml` added
- [x] `docs/ai-touchpoints.md` unchanged (no backend change)
- [x] Parity: `backend/CLAUDE.md` + `frontend/CLAUDE.md` "no code yet" notes cleared in the same
      commit as their 3 `.mdc` mirrors (`backend-fastapi`, `frontend-nextjs`, `testing`)
- [x] `README.md` status updated
- [x] PM `Status: Accepted`

**PM acceptance (2026-08-29):** The client is thin and correct — one API module, Supabase only for
the session, the §15 invariants (no JSON export, watermark on Free, price-edit-is-PATCH) are all
directly tested. 8 Jest tests + typecheck + production build pass in CI with no backend. SSR of the
preview is a logged follow-up, not a blocker for the skeleton. **Accepted.**

---

## Technical specification (Architect)

### Stack

Next.js 15 (App Router), React 19, TypeScript, Tailwind 3. `@supabase/ssr` for cookie-based sessions
+ a `middleware.ts` route guard. Jest + `@testing-library/react` for tests.

### Layout added (`frontend/`)

```
src/
  middleware.ts                     # redirect guard via updateSession()
  lib/
    supabase/{client,middleware}.ts # browser client + session refresh/guard
    api.ts                          # THE only backend caller; apiFetch + typed `api.*`
    types.ts  format.ts  useApi.ts
  app/
    layout.tsx  globals.css
    sign-in/page.tsx
    page.tsx            (dashboard list)
    settings/page.tsx   (profile + packages, PUT /v1/me)
    proposals/new/page.tsx
    proposals/[id]/page.tsx   (editor)
  components/
    Nav.tsx  PreviewPane.tsx  SectionForms.tsx  WatermarkBanner.tsx
jest.config.mjs  jest.setup.ts  Dockerfile  .env.example
```

### Inference & money (cross-ref `docs/ai-touchpoints.md`)

- **No LLM call from the client.** Generate/regenerate are plain `POST`s to FastAPI; the model runs
  server-side (a mock in Wave 3). The client never sees `proposal_json`.
- **The client shows prices, never computes them.** `SectionForms` sends edited amounts as a `PATCH`
  `pricing` body; the server persists them as-is (user-authored). A price edit does not hit
  generate/regenerate — asserted by `SectionForms.test.tsx`.
- `docs/ai-touchpoints.md` unchanged; `docs/architecture-sequences.md` build note (from S-001) still holds.

### Auth

`@supabase/ssr` `createServerClient` in `middleware.ts` refreshes the session cookie and redirects
unauthenticated users (anything outside `/sign-in`, `/auth/*`) to `/sign-in`. `createBrowserClient`
(lazy, inside handlers — never at render, so a build-time prerender with no env doesn't construct it)
provides the access token to `api.ts`.

### Rendering note (accepted tradeoff)

`frontend/CLAUDE.md` says "Server Components by default". The skeleton's data pages are **client
components + hooks** (`useResource`) because `@supabase/ssr` server-component data fetching adds
setup this slice doesn't need to prove the flow. Moving the dashboard list + editor preview to
Server Components is logged in `docs/roadmap.md`.

### Architect checklist

- [x] No `/v1` contract change; client matches the S-001 DTOs (`types.ts` mirrors `app/schemas`)
- [x] No LLM / money logic in the client
- [x] `proposal_json` never requested or rendered
- [x] Supabase used only for the session; all data via `api.ts`
- [x] No secrets — `.env.example` only; CI uses fake `NEXT_PUBLIC_*`

### Risks / tradeoffs

- **Client-side data fetching** (see above) — a11y/SEO/perf cost for a logged-in app tool is low;
  SSR migration is roadmap.
- **`middleware.ts` calls `supabase.auth.getUser()` on every request** — one network call to Supabase
  per navigation. Acceptable for v0; can be tightened with `getSession()` + JWT age check later.
- **No E2E** — Playwright against Compose is a later slice; unit + build coverage only here.

---

## Links

- Test plan: [`TP-S-002-nextjs-client.md`](../test-plans/TP-S-002-nextjs-client.md)
- Test report: [`TR-S-002-nextjs-client.md`](../test-reports/TR-S-002-nextjs-client.md)
- ADR: none (no architecture decision beyond S-001 / ADR-001)

---

## Changelog

| Date | Agent | Change |
|---|---|---|
| 2026-08-29 | PM | Created slice, 11 AC (auth guard, API-only, settings, generate, editor invariants, CI) |
| 2026-08-29 | Architect | Stack + layout + auth (`@supabase/ssr` + middleware) + client-rendering tradeoff |
| 2026-08-29 | Builder | `frontend/` Next.js 15 app: middleware, api module, 5 routes, 4 components, Jest config, Dockerfile, `frontend-tests.yml`; cleared the stale nested-CLAUDE.md notes across all 5 parity files |
| 2026-08-29 | Tester | 8 Jest tests + `tsc --noEmit` + `next build` all pass; 11/11 AC → Ship |
| 2026-08-29 | PM | §15 invariants tested, build green in CI without a backend → **Accepted** |
