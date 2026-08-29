# TP-S-002: Next.js web client — Test plan

| Field | Value |
|---|---|
| **Slice** | S-002 |
| **Author** | Tester |
| **Date** | 2026-08-29 |

---

## Scope

The `frontend/` Next.js client: auth guard, the single API module, and the editor invariants from
`mvp-spec.md` §15 (no JSON export, watermark on Free, price-edit-is-a-PATCH). No backend runs — the
API module's `fetch` is stubbed and a fake token is injected.

---

## Test strategy

| Layer | Tool | Focus |
|---|---|---|
| API module | Jest, `fetch` mock | only calls the FastAPI base URL; attaches / omits the bearer; `ApiError` on non-2xx |
| Components | Jest + `@testing-library/react` + `user-event` | preview has no export affordance; watermark on Free; price edit → `PATCH pricing` (not regenerate); section edit → `PATCH sections.*` |
| Whole app | `tsc --noEmit`, `next build` | types sound, production build succeeds with fake `NEXT_PUBLIC_*` and no backend |

Environment (`jest.setup.ts` + CI env): `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/v1`,
fake `NEXT_PUBLIC_SUPABASE_*`. No network.

---

## AC → planned tests

| AC# | Approach | Test |
|---|---|---|
| 1–2 | Manual — middleware guard + sign-in handlers use Supabase, redirect on success | M-001 (code review + `next build` proves middleware compiles) |
| 3 | Automated | `src/lib/__tests__/api.test.ts` — URL is `${API_BASE}/…`, `Authorization: Bearer` set/omitted |
| 4 | Manual — settings form calls `api.putMe`, client-side amount validation (`toMinor`) | M-002 |
| 5 | Manual — new-proposal form builds the `ProposalCreate` body per mode, `402` → message | M-003 |
| 6 | Automated | `PreviewPane.test.tsx` — renders sections; no `export json` / `copy source` / `proposal_json` text |
| 7 | Automated | `SectionForms.test.tsx::editing a section field PATCHes sections.*` |
| 8 | Automated | `SectionForms.test.tsx::editing a price sends a plain PATCH (pricing), never a regenerate` |
| 9 | Automated | `PreviewPane.test.tsx` — Free: watermark + no follow-up; paid: clean |
| 10 | Manual — editor buttons call `api.regenerate` / `api.duplicate`; PDF shows the Wave 4 note | M-004 |
| 11 | Manual/CI — `npm run typecheck && npm test && npm run build` | M-005 |

---

## Manual checklist

- [ ] M-001: `src/middleware.ts` guards all routes bar `/sign-in`, `/auth/*`; sign-in page has email + Google, no OTP field
- [ ] M-002: settings → `api.putMe`; a non-numeric package amount blocks the request with an inline error
- [ ] M-003: new-proposal → `api.createProposal` with `package_ids` / `hourly` / `fixed` per the selected mode; `402` renders the plan-limit line
- [ ] M-004: Regenerate/Duplicate buttons wired; "Download PDF" → "arrives in Wave 4"
- [ ] M-005: `npm run typecheck` (exit 0), `npm test` (8 pass), `npm run build` (7 routes, middleware) all green
