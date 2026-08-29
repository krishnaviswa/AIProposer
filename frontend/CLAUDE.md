# Frontend rules (Next.js)

> Mirrors `.cursor/rules/frontend-nextjs.mdc` (Cursor `globs: frontend/**/*`), plus the frontend
> half of `.cursor/rules/testing.mdc`. Keep in sync — see the parity table in the root
> [`CLAUDE.md`](../CLAUDE.md).

> No frontend code exists yet — Wave 3 (Phase 1) creates it. This file is the standing contract.

## Boundary

The web client is **UI only**. It calls FastAPI `/v1` and nothing else. No business logic, no
pricing math, no direct LLM / Razorpay / Supabase-DB calls. The Supabase client SDK is used **only**
for the auth session (obtain the JWT); every data operation goes through FastAPI.

## Rendering

- Server Components by default (dashboard list, proposal detail shell).
- `"use client"` only for: the split editor, forms, checkout redirect, hooks, localStorage.

## Structure

- Pages: `src/app/**/page.tsx` · Components: `src/components/` · API client: `src/lib/api.ts` (one place;
  attaches `Authorization: Bearer <supabase JWT>`; do not scatter `fetch`).

## Proposal editor (spec §3, §15)

- Split UI: PDF-like **preview** + **section forms** (right rail / full-screen on mobile), bound to the
  same fields. `PATCH` sends allowlisted fields only.
- **No JSON editor. No "Export JSON" / "Copy source" control. Ever.**
- Free plan: watermark on preview **and** the downloaded PDF; no follow-up-email copy button.
- Editing a price field is a normal `PATCH` — never triggers a regenerate.

## Auth

Session + JWT from the Supabase client SDK; `api.ts` attaches the bearer token. On `401`, route the
user back through Supabase sign-in (email verified + Google only).

## UI

Tailwind. Generated copy is editable text the user owns. Reuse primitives; JSDoc on components.

## Local commits

Never commit on `main` — feature branch + PR. `.githooks/pre-commit` enforces this.

## Testing

> Mirrors `.cursor/rules/testing.mdc` (frontend half). Keep in sync.

- Jest + RTL, colocated under `__tests__/`. Test behavior, not implementation.
- `AI_PROVIDER=mock` and friends — no live vendors, no Supabase network.
- Assert product invariants: no "Export JSON" control exists; free-plan preview shows the watermark;
  editing a price field calls `PATCH`, not regenerate.
- Default run: only the Jest files for the area changed (`npx jest <path>`). Full `npm test` before
  merge, when `src/lib/api.ts` changed, or when asked.
- Browser e2e (later): Playwright (Python) under `backend/tests/e2e/`, `E2E=1`, not a merge gate. No Cypress/Selenium.
