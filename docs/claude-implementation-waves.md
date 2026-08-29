# Claude implementation waves (AIProposer)

**How to use:** Paste **one wave** into Claude Code per session (or finish a wave, then paste the next). Claude may split a wave into S-000 / S-001 internally. Do not paste Wave 3 until Wave 1–2 artifacts exist in the repo. Attach `mvp-spec.md` on every wave.

**Frozen v0 product spec:** [`mvp-spec.md`](../mvp-spec.md) (do not change prices, SKUs, or included counts in these waves).

**Pattern repo (adapters + Cursor↔Claude parity + PM → Architect → Builder → Tester only — not the product):**  
https://github.com/krishnaviswa/MEngPlat.git

**AUTH OVERRIDE (fill once in Wave 1; later waves inherit):**

- [ ] Frozen spec: Supabase email verified + Google. No SMS.
- [ ] India +91 / INR rail: Google + phone SMS OTP via Supabase (India SMS gateway). Non-India: Google + verified email. No authenticator TOTP. No international SMS in v0.
- [ ] Other: ________

If unchecked, implement email + Google and keep SMS OTP as `blocked-on-decision` in `docs/roadmap.md` (Wave 2).

---

## End picture (canonical — Wave 1 must write this down, not invent it)

**v0 runtime:** Browser (Next.js) → FastAPI `/v1` → Supabase Auth JWT, Postgres, Storage; Razorpay webhooks into FastAPI; **one** LLM call behind a Python adapter. Flutter and Stripe are **out** of this picture.

**AI inference happens in two v0 places only:** successful `POST /v1/proposals` (generate) and `POST /v1/proposals/{id}/regenerate`. Prices are assembled in FastAPI **before** the model runs; any money the model returns is stripped. PATCH, PDF, download, duplicate, checkout, and webhooks **do not** call the LLM.

```mermaid
sequenceDiagram
  actor U as Freelancer
  participant W as Next.js
  participant A as FastAPI
  participant Auth as Supabase Auth
  participant DB as Postgres
  participant LLM as LLM adapter
  participant Store as File storage
  participant Pay as Razorpay

  U->>W: Sign in (email verify and/or Google)
  W->>Auth: Session
  W->>A: API + JWT
  A->>Auth: Validate JWT

  U->>W: Packages/hours (their amounts)
  W->>A: PUT /v1/me
  A->>DB: Save packages/rate

  U->>W: Brief + Generate
  W->>A: POST /v1/proposals
  A->>DB: Quota check; persist user prices
  Note over A,LLM: AI touchpoint 1 — structured copy only
  A->>LLM: Prompt + schema (no authority over amounts)
  LLM-->>A: JSON copy
  A->>A: Overwrite pricing[].amount from user
  A->>DB: Save proposal_json; increment usage
  A-->>W: View DTO (forms + preview, not export JSON)

  U->>W: Edit copy or prices
  W->>A: PATCH allowlist
  Note over A: No LLM, no quota
  A->>DB: Update; invalidate pdf_url

  U->>W: Download PDF
  W->>A: GET .../pdf
  A->>Store: Render if cache miss
  Note over A: No LLM, no quota

  U->>W: Pay Starter
  W->>A: POST /v1/billing/checkout-session
  A->>Pay: Create subscription
  Pay->>A: Webhook (HMAC, idempotent)
  A->>DB: Plan + period anchor
```

**v0 AI allowlist**

| Event | Path | LLM | Quota |
|---|---|---|---|
| Generate | `POST /v1/proposals` | Yes (after user prices persisted) | 1 if success; 0 if fail/empty |
| Regenerate | `POST /v1/proposals/{id}/regenerate` | Yes (same price overwrite rules) | 1 if success |
| Sign-in / JWT | Supabase + FastAPI verify | No | 0 |
| Save packages/rate | `PUT /v1/me` | No | 0 |
| List/detail | `GET /v1/proposals` | No | 0 |
| Edit copy or prices | `PATCH` allowlist | No | 0 |
| PDF | `GET /v1/proposals/{id}/pdf` | No | 0 |
| Duplicate | clone inputs + last server JSON | No until Generate | 0 |
| Checkout / webhook | Razorpay | No | 0 |
| Competitor upload extract | v1.1 only | Yes (later) | TBD — not v0 |

---

## Wave 1 — architecture + sequences (no app code, no parity yet)

```text
You are the architect for AIProposer. Attached mvp-spec.md is frozen v0. Do not change prices, SKUs, or scope.

Pattern repo (clone or fetch as read-only reference — copy adapter/workflow shape later, never MerchantHub product):
https://github.com/krishnaviswa/MEngPlat.git

GOAL OF THIS WAVE ONLY
Write the missing architecture pack. No FastAPI/Next.js feature code. No Cursor↔Claude parity files yet (that is Wave 2).

AUTH OVERRIDE (human fills; if empty, document email+Google as v0 and SMS OTP as open):
- [ ] Frozen spec: Supabase email verified + Google. No SMS.
- [ ] India +91 / INR rail: Google + phone SMS OTP via Supabase (India SMS gateway). Non-India: Google + verified email. No authenticator TOTP. No international SMS in v0.
- [ ] Other: ________

CREATE
- docs/architecture.md — system context, container diagram, trust boundaries, what is in/out of v0.
- docs/architecture-sequences.md — mermaid (or equivalent) for every v0 user journey below. Mark every LLM hop with a note "AI inference".
- docs/ai-touchpoints.md — table: event, path, LLM yes/no, quota yes/no, who computes money, failure behavior.
- README.md — short index with links to mvp-spec.md, the three docs above, and a stub for docs/roadmap.md (file may be empty until Wave 2).

END PICTURE (v0) — transcribe and refine, do not replace
Actors: one freelancer (owner of the quote). Systems: Next.js (UI only), FastAPI (all business logic), Supabase Auth + Postgres + Storage, Razorpay, one LLM provider via Python adapter, PDF renderer in FastAPI/worker, email for verify/receipts. Later (do not draw as v0 runtime): Flutter, Stripe, infographic job, competitor-upload OCR.

AI INFERENCE — v0 allowlist (if a diagram shows LLM elsewhere, it is wrong)
1. POST /v1/proposals — after quota check and after FastAPI has copied user package/hourly amounts into the payload. Model returns copy fields only. FastAPI overwrites any price the model emits. No streaming. Success → 1 quota. Fail/empty → 0 quota.
2. POST /v1/proposals/{id}/regenerate — same rules, 1 quota.

NOT AI (must appear on sequences as FastAPI-only)
- Auth / JWT validate
- PUT/GET /v1/me (packages, rate, quote currency)
- GET list/detail (view DTO for preview+forms; never "export JSON")
- PATCH allowlisted fields (copy or prices). Price edits do not call LLM. Invalidate PDF cache.
- GET /v1/proposals/{id}/pdf — render-from-structured-data, cache pdf_url
- Duplicate proposal — clone inputs + last server JSON, no LLM until Generate
- POST checkout-session + Razorpay webhook (HMAC, WebhookEvents idempotency)
- WhatsApp = wa.me + link, not WhatsApp Cloud API

REQUIRED SEQUENCES
1. Sign in (per AUTH OVERRIDE) → JWT on API
2. Save rates/packages
3. Generate (full hop list including price assembly BEFORE llm)
4. Edit without generate
5. PDF first hit vs cache hit
6. Subscribe India Starter (Razorpay)
7. Regenerate
8. One "v1.1 ghost" diagram: competitor upload + extract — labeled NOT v0, optional second AI hop

CONSTRAINTS FROM SPEC
- Money never originates in the model. No ×1.6/×2.5.
- JSON is a server artifact.
- India-first = Razorpay how we charge the freelancer; quote currency is independent.
- Cite mvp-spec.md sections in the docs (data model §6, API §7, prompt/pricing §9, leak §15, injection §16).

Canonical mermaid and the AI-touchpoint table already live in docs/claude-implementation-waves.md in this repo — copy them into the three architecture files and expand, do not contradict them.

DONE WHEN
The three docs exist, README links them, a reviewer can see where inference runs without reading the spec cover to cover. Stop. Do not start Wave 2 unless asked.
```

---

## Wave 2 — agent workflow + Cursor↔Claude parity (no product features)

```text
Continue AIProposer. mvp-spec.md is frozen v0. Wave 1 docs (docs/architecture.md, docs/architecture-sequences.md, docs/ai-touchpoints.md) already exist — do not contradict them.

Pattern repo (parity script, PM/Architect/Tester roles, templates — not reviews/TOTP/custom JWT):
https://github.com/krishnaviswa/MEngPlat.git

GOAL OF THIS WAVE ONLY
Bootstrap how Cursor and Claude Code stay in sync, and the slice cycle. Still no generate/PDF/Razorpay feature code.

CLONE/READ from MEngPlat and ADAPT (rewrite MerchantHub examples to this product):
- .cursor/rules/ + .cursor/rules/agents/ (workflow + PM + architect + tester)
- CLAUDE.md + nested CLAUDE.md + .claude/agents/product-manager.md, architect.md, tester.md
- AGENTS.md
- scripts/check_agent_config_sync.py + SYNC_GROUPS + parity table in root CLAUDE.md
- pre-commit + CI workflow that runs the sync script on PRs
- docs/agents/ templates: slices, adrs, test-plans, test-reports

CYCLE (mandatory after this wave)
PM (slice brief) → Architect (tech spec) → Builder (code) → Tester (report) → PM (accept)
No Builder until Architect has filled API/schema against Wave 1 diagrams. Never commit on main.

README
Index must link: mvp-spec.md, Wave 1 architecture docs, AGENTS.md, CLAUDE.md parity table, docs/agents/, docs/roadmap.md, and this file docs/claude-implementation-waves.md.

docs/roadmap.md
Seed deferred items (Flutter, Stripe, packs, competitor compare, infographics, seats, Hindi, authenticator TOTP, SMS OTP if AUTH still open, public name, model bake-off, single-session, prompt cache, screenshot teaser, Scale). Each row: status, target version, why not v0, spec pointer. New "later" ideas from chat go here in the same PR; README already points here. Do not unfreeze mvp-spec.md.

SLICE
S-000-agent-bootstrap: AC = parity check would fail on a one-sided rule edit; templates exist; README + roadmap done. Run full cycle. Stop after PM Accepted. Do not start FastAPI JWT/proposals unless asked (Wave 3).
```

---

## Wave 3 — platform skeleton (auth, CRUD, quotas, mocks — LLM adapter dark)

```text
Continue AIProposer. Frozen: mvp-spec.md. Binding pictures: docs/architecture.md, docs/architecture-sequences.md, docs/ai-touchpoints.md. Binding process: Wave 2 parity + slice cycle. Pattern repo: https://github.com/krishnaviswa/MEngPlat.git (AI/payments/storage/email adapters + SlowAPI + HMAC + Alembic + pytest mocks only).

GOAL OF THIS WAVE
S-001-style foundation that matches the sequences BUT keep the LLM adapter returning mock structured copy (or unplugged). Prove JWT, me/packages, proposals CRUD, PATCH allowlist, quota counter without a live model. No Razorpay live keys; webhook stub + mock payment adapter is enough.

MUST
- FastAPI /v1, Next.js talks only to FastAPI
- Supabase JWT verify only (no passlib custom auth)
- Auth per AUTH OVERRIDE recorded in Wave 1
- Prices from user packages/hours in DB; PATCH prices does not call LLM
- View DTO only; no Export JSON
- Rate limit /v1/proposals
- CI: no live LLM, no live Razorpay
- Feature branch + PR; update slice + tests; do not commit main

MUST NOT
- Wire real provider generate (Wave 4)
- PDF renderer required only if it does not pull you into Wave 4; otherwise stub pdf_url
- Flutter, Stripe, uploads, infographics, seats

Architect must cite ai-touchpoints.md: this wave has zero production AI hops. Stop when Tester maps ACs and PM can accept.
```

---

## Wave 4 — AI generate + cached PDF + Razorpay (inference only at documented hops)

```text
Continue AIProposer. Frozen spec + Wave 1 architecture/touchpoints + Wave 2 workflow + Wave 3 skeleton are in the repo. Pattern repo: https://github.com/krishnaviswa/MEngPlat.git (swap mock AI/payment adapters for real ports the same way MEngPlat does).

GOAL OF THIS WAVE
Turn on the two v0 AI hops and the money/PDF paths. If a new LLM call appears on PATCH, PDF, login, or webhook, reject the design.

IMPLEMENT (slices as you see fit, still PM→Architect→Builder→Tester each)
1. Real LLM adapter: structured output, max_tokens, system prompt cache if provider allows, strip/overwrite prices, injection guards (mvp-spec §16), increment usage only on success.
2. POST generate + POST regenerate per §7; no streaming JSON.
3. Server-side PDF from structured data, cache, invalidate on PATCH.
4. Razorpay checkout + HMAC webhook + idempotency; India Free + Starter ₹500/20; watermarked free; no follow-up email on free.
5. Next.js split preview + forms; watermark on free.

DONE
ai-touchpoints.md still accurate; tests without live keys in CI; README links updated; deferred work only in docs/roadmap.md. Do not start v1.1 competitor compare or Flutter.
```
