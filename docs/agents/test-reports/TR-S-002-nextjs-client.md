# TR-S-002: Next.js web client — Test report

| Field | Value |
|---|---|
| **Slice** | S-002 |
| **Author** | Tester |
| **Date** | 2026-08-29 |
| **Recommendation** | **Ship** |

---

## Summary

**8 Jest tests pass**, `tsc --noEmit` is clean, and `next build` produces all 7 routes + middleware.
The three `mvp-spec.md` §15 invariants are directly asserted: the preview has no JSON / export
affordance, the Free plan shows the "NOT FOR SENDING" watermark and hides the follow-up email, and
editing a price field sends a plain `PATCH pricing` — never a regenerate. The API module only ever
targets the FastAPI base URL and attaches the Supabase bearer. No backend or real Supabase project
is needed for any of this.

---

## AC coverage matrix

| AC# | Description | Type | Test reference | Result |
|---|---|---|---|---|
| 1 | Middleware redirects unauthenticated → `/sign-in` | M | M-001 (`src/middleware.ts` + `lib/supabase/middleware.ts`; compiles in `next build` — "ƒ Middleware 62.3 kB") | Pass |
| 2 | Sign-in: email/password + Google, no OTP | M | M-001 (`src/app/sign-in/page.tsx`) | Pass |
| 3 | Client calls only FastAPI `/v1` with bearer | A | `src/lib/__tests__/api.test.ts` (3 tests) | Pass |
| 4 | Settings → `PUT /v1/me`, client-side amount validation | M | M-002 (`src/app/settings/page.tsx`, `toMinor`) | Pass |
| 5 | New-proposal → `POST /v1/proposals` per mode, `402` message | M | M-003 (`src/app/proposals/new/page.tsx`) | Pass |
| 6 | Editor = preview + section forms; no JSON view / Export JSON | A | `src/components/__tests__/PreviewPane.test.tsx::renders … without exposing any JSON / export affordance` | Pass |
| 7 | Section edit → `PATCH sections.*` | A | `SectionForms.test.tsx::editing a section field PATCHes sections.*` | Pass |
| 8 | Price edit → `PATCH pricing`, not regenerate | A | `SectionForms.test.tsx::editing a price sends a plain PATCH (pricing), never a regenerate` | Pass |
| 9 | Free → watermark + no follow-up; paid → clean | A | `PreviewPane.test.tsx` (2 tests: Free, paid) | Pass |
| 10 | Regenerate / Duplicate wired; PDF → Wave 4 note | M | M-004 (`src/app/proposals/[id]/page.tsx`) | Pass |
| 11 | `typecheck` + `jest` + `next build` green, no backend | A/M | M-005 + `frontend-tests.yml` | Pass |

**Coverage:** 11 / 11 AC — 6 automated, 5 manual (code review + build).

---

## Frontend tests

### Added (8 tests, 3 suites)

- `src/lib/__tests__/api.test.ts` — base-URL-only, bearer set/omitted, `ApiError` on non-2xx
- `src/components/__tests__/PreviewPane.test.tsx` — no export affordance; Free watermark + hidden
  follow-up; paid renders clean
- `src/components/__tests__/SectionForms.test.tsx` — price edit → `PATCH pricing` (not regenerate);
  section edit → `PATCH sections.*`

### Run output

```
$ cd frontend && npx jest
PASS src/lib/__tests__/api.test.ts
PASS src/components/__tests__/PreviewPane.test.tsx
PASS src/components/__tests__/SectionForms.test.tsx
Test Suites: 3 passed, 3 total
Tests:       8 passed, 8 total

$ npx tsc --noEmit      # exit 0
$ npx next build        # ✓ Compiled successfully — 7 routes + Middleware
```

---

## Backend tests

None — S-002 adds no backend code. The S-001 suite (42 tests) is unaffected.

---

## Manual / integration

| ID | Check | Result |
|---|---|---|
| M-001 | Middleware guard + sign-in (email + Google, no OTP) | Pass |
| M-002 | Settings → `api.putMe`; bad amount blocked client-side | Pass |
| M-003 | New-proposal body per pricing mode; `402` → plan-limit line | Pass |
| M-004 | Regenerate/Duplicate wired; "Download PDF" → "arrives in Wave 4" | Pass |
| M-005 | `typecheck` + `jest` + `build` | Pass |

---

## Regressions

None. Backend untouched. Parity: the stale "no code yet" notes in `backend/CLAUDE.md` +
`frontend/CLAUDE.md` were cleared **together with** their three `.mdc` mirrors (`backend-fastapi`,
`frontend-nextjs`, `testing`) so the sync check passes — this closes S-001's follow-up #1.

---

## Gaps / rework items (non-blocking)

1. **Data pages are client components + hooks**, not Server Components — contrary to
   `frontend/CLAUDE.md`'s "Server Components by default". Deliberate for the skeleton; SSR migration
   is in `docs/roadmap.md`.
2. **No E2E** — Playwright against Compose is a later slice.
3. **`middleware` calls `getUser()` per request** — one Supabase round-trip per navigation; fine for
   v0, tightenable later.
4. Google OAuth `redirectTo` points at `/` — a dedicated `/auth/callback` handler is a small later add.

---

## Sign-off

- [x] All 11 AC mapped (6 automated, 5 review/build)
- [x] Client talks only to FastAPI `/v1` — asserted
- [x] No "Export JSON" / JSON view — asserted
- [x] Price edit is a PATCH, not a regenerate — asserted
- [x] `docs/ai-touchpoints.md` unchanged; no backend behaviour added
- [x] Ready for PM acceptance
