# AIProposer — Roadmap (deferred work)

Everything here is **out of the frozen v0 scope** in [`../mvp-spec.md`](../mvp-spec.md). This file is
the *only* place new "later" ideas are recorded — they go here in the **same PR** as the discussion,
never as edits to `mvp-spec.md` (frozen) and never as a new prose `.md`.

**Status values:** `blocked-on-decision` (needs a human call) · `deferred` (agreed, not scheduled) ·
`planned` (will happen in a named wave) · `feature-flag` (code path exists but off) · `idea` (not agreed).

| Item | Status | Target | Why not v0 | Pointer |
|---|---|---|---|---|
| **SMS / phone OTP auth rail (India +91)** | `blocked-on-decision` | TBD | AUTH OVERRIDE in the wave file was left unfilled; frozen spec ships email-verified + Google only. Needs a product decision before it can be scheduled. Only sequence 1 changes if adopted. | `mvp-spec.md` §3.1, §13.1; [`architecture.md`](architecture.md) "AUTH OVERRIDE" |
| **Public product name / domain** (rename off `AIProposer`) | `blocked-on-decision` | Before launch / marketing | Name collision with the live product aiproposer.com (Upwork bid-letter tool, USD). Git name is fine internally; a public brand is not chosen. | `mvp-spec.md` §0 (repo-name note), §14.1 |
| Quota micro-tier (~15/mo, between Free 3 and Starter 20) | `idea` | TBD | Not in the frozen SKU table; would change §5.1 economics. Revisit on conversion data. | `mvp-spec.md` §5.1 |
| Flutter / any mobile client | `deferred` | post-v0 | v0 is backend + web only. A mobile client must speak the same FastAPI API — no business logic moves out of FastAPI for it. | `mvp-spec.md` §0.2, §3.2, §8, §18.1 |
| Stripe / global `$` checkout | `deferred` | When Global SKUs ship | One payment rail for v0 (Razorpay, INR). Global Starter/Pro list prices exist in §5.1 but are "when Stripe exists". | `mvp-spec.md` §0.5, §5.1, §8 |
| Proposal packs / overage | `deferred` | v1.1 | v0 is hard caps, no overage. Packs must be priced **above** loaded COGS (India floor ₹20, Global $0.20) — never ₹8. | `mvp-spec.md` §0.6, §5, §5.2 |
| Competitor quote compare (upload PDF/image → extract → side-by-side) | `feature-flag` | v1.1, **Pro+** | Vision/OCR is not ₹1.2 — dumping images/long PDFs into a frontier vision model blows the loaded ₹8 bag. Adds a **second** AI hop. Keeping it out keeps the v0 injection surface and COGS small. | `mvp-spec.md` §0.7, §3.2, §17; [`ai-touchpoints.md`](ai-touchpoints.md) "v1.1 — deferred AI"; [`architecture-sequences.md`](architecture-sequences.md) §8 ghost |
| Infographic PNG one-pager | `deferred` | v1.1, **Pro+** | Built from the *same* structured record; optional tiny LLM pass to shorten labels only. Client one-pager first, not price-posting to social. | `mvp-spec.md` §3.2, §10 |
| General file uploads | `deferred` | v1.1 | No upload surface in v0 — every upload is injection + COGS risk. v1.1 passes only **extracted JSON** into a second small prompt, never raw bytes. | `mvp-spec.md` §3.2, §16, §17 |
| Seats / `workspaces` / "team" | `deferred` | post-v0 (P1) | One seat, one quota, one leak surface for v0. Sharing a single Starter login across a pod is the main abuse path — do not sell "team" until seats exist. | `mvp-spec.md` §0.1, §1 (P1), §15.1 |
| "Scale" plan (400 generates) | `deferred` | post-v0 | Depends on seats. Not v0. | `mvp-spec.md` §5.1 |
| Hindi / Devanagari UI or output | `deferred` | v1.2, on a demand signal | Devanagari is 2–4× the token budget. The `language` column is added now with value `en`; Hinglish *tone* is allowed in v0. Local feel = Razorpay + INR + WhatsApp link. | `mvp-spec.md` §3.1, §4, §13.4 |
| Authenticator TOTP / MFA | `deferred` | post-v0 | Not in frozen scope. MEngPlat's TOTP/passlib auth is explicitly **not** copied — Supabase Auth stays the identity layer. | `mvp-spec.md` §18.2 |
| Single-session / one-login enforcement | `deferred` | post-v0 | v0 anti-sharing = email verify + Google + rate limit. A 1-session policy comes with seats. | `mvp-spec.md` §15.5 |
| Distributed single-flight lock on generate | `deferred` | Wave 4 / multi-instance | S-001's "max 1 concurrent LLM call per user" is an in-process `asyncio.Lock` — correct for the single-instance v0 deploy, not across replicas. | `mvp-spec.md` §16; `docs/agents/slices/S-001-platform-skeleton.md` |
| Supabase user-deletion sync | `deferred` | post-v0 | FastAPI provisions a local `users` row on first valid JWT (ADR-001). A valid token for a since-deleted Supabase user would re-create the row. A "user deleted" webhook / reconciliation closes this. | `docs/agents/adrs/ADR-001-supabase-jwt-verification.md` |
| Web client SSR migration | `deferred` | post-skeleton | S-002's data pages (dashboard list, editor preview) are client components + hooks. `frontend/CLAUDE.md` wants Server Components by default. Move list/detail to RSC with `@supabase/ssr` server-component data fetching. | `docs/agents/slices/S-002-nextjs-client.md`; `frontend/CLAUDE.md` |
| Web client E2E (Playwright vs Compose) | `deferred` | post-skeleton | S-001/S-002 have unit + build coverage only. A Playwright suite against `docker compose` (mock vendors) covers the sign-in → generate → edit → status flow end to end. | `.cursor/rules/testing.mdc` |
| Signed short-TTL storage URLs (S3 / Supabase Storage adapter) | `deferred` | before GA | `LocalStorageProvider.signed_url` returns `/uploads/<key>` — fine for Compose, not a private signed URL. A real storage adapter gives short-TTL signed links for the cached PDFs. | `docs/agents/slices/S-003-live-ai-and-pdf.md`; `mvp-spec.md` §8, §15 |
| Model bake-off — pin `AI_MODEL` | `planned` | before GA | S-003 defaults to `claude-haiku-4-5` (ADR-002, meets the §4 cost target). The §16 ~20-brief benchmark on structure + hallucination picks the final pin. | `mvp-spec.md` §4, §13.3, §16; `docs/agents/adrs/ADR-002-model-choice-and-structured-output.md` |
| Prompt-cache hit-rate check | `planned` | with the bake-off | Verify `usage.cache_read_input_tokens` is non-zero for the cached system prompt on the pinned model (may need a larger prompt for some models). | ADR-002; `mvp-spec.md` §4 |
| Razorpay Checkout.js integration + `/auth/callback` | `deferred` | before GA | S-004 wires `checkout-session` and opens `window.Razorpay` when `checkout.js` + a real key are present; the hosted-checkout script load, success/failure handlers, and a proper Google OAuth callback route are the finishing touches. | `docs/agents/slices/S-004-razorpay-and-web-money.md` |
| Model bake-off + pin | `planned` | Wave 4 / before GA | Benchmark ~3 mid-tier models on ~20 real briefs; pin on structure + hallucination, not cheapness; swap behind the AI adapter. Fewer included units *assumes* this bar is met. | `mvp-spec.md` §4, §13.3, §16 |
| System-prompt caching | `planned` | Wave 4 | Cache the ~600–1,000-token system prompt where the provider allows; part of the ≤ $0.012/generate target. | `mvp-spec.md` §4, §9 |
| Screenshot-only teaser (no selectable text on free preview) | `deferred` | TBD | Weak anti-extraction (OCR defeats it), a11y cost, hurts conversion. Free preview only, optional. The real defense is making **JSON and the system prompt** hard to get, and free output obviously incomplete. | `mvp-spec.md` §15.2, §15.4 |
| `user-select: none` on the free preview | `idea` | TBD | Weak; skip if it hurts trust. | `mvp-spec.md` §15.4 |
| Annual billing | `deferred` | v1.1 "if easy" | Not v0. | `mvp-spec.md` §3.2 |
| PostHog product analytics | `planned` | Late in the v0 build | Can land late; not a launch blocker. Sentry is the v0 error tool. | `mvp-spec.md` §8 |

## Nested `CLAUDE.md` split (tooling, not product)

When Wave 3 adds backend code, split `backend/CLAUDE.md` into nested `backend/app/models/CLAUDE.md`
and `backend/app/services/CLAUDE.md` (mirroring new `.cursor/rules/database.mdc` /
`ai-and-integrations.mdc`), and add the new pairs to `SYNC_GROUPS` in
`scripts/check_agent_config_sync.py` and the parity table in the root `CLAUDE.md`.
