# AIProposer

India-first, single-operator **quote / proposal generator**. A freelancer pastes a client brief,
confirms **their own** package prices or hourly rate, and leaves with a sendable proposal
(PDF-like preview + cached PDF) — not a chat transcript, not a JSON export.

> `AIProposer` is the internal git name only. Public product name and domain are deferred
> (there is a known name collision with a live product — see `mvp-spec.md` §14 and `docs/roadmap.md`).

**This file is the map.** Everything else in the repo is reachable from the links below — start here,
then follow the branch you need.

---

## Repository layout

```
AIProposer/
├─ mvp-spec.md            FROZEN v0 spec — the source of truth
├─ README.md              ← you are here: the index
├─ AGENTS.md              repo map for AI agents (Cursor + Claude Code)
├─ CLAUDE.md              Claude Code project rules + multi-agent workflow + parity table
│
├─ backend/               FastAPI service — ALL business logic, /v1 REST, adapters, Alembic
│  └─ CLAUDE.md           backend standing contract (FastAPI conventions, testing)
├─ frontend/              Next.js 15 App Router web client — UI only, talks to /v1
│  └─ CLAUDE.md           frontend standing contract (App Router, boundary, testing)
│
├─ docs/
│  ├─ architecture.md            containers, trust boundaries, in/out of v0
│  ├─ architecture-sequences.md  mermaid sequence per v0 journey
│  ├─ ai-touchpoints.md          where the LLM is / isn't called (authoritative)
│  ├─ roadmap.md                 deferred / not-v0 work — the only place "later" ideas live
│  ├─ NEXT-STEPS.md              current pre-launch checklist + open decisions
│  ├─ claude-implementation-waves.md   the wave-by-wave build plan
│  ├─ CLAUDE.md                  documentation & spec rules (who may edit what)
│  └─ agents/                    live workflow artifacts
│     ├─ slices/        S-000 … S-006 briefs (+ _TEMPLATE.md)
│     ├─ adrs/          ADR-001 … ADR-004 (+ _TEMPLATE.md)
│     ├─ test-plans/    TP-S-00X (+ _TEMPLATE.md)
│     └─ test-reports/  TR-S-00X (+ _TEMPLATE.md)
│
├─ .cursor/rules/         Cursor's mirror of the rules + roles
├─ .claude/agents/        Claude Code's PM / Architect / Tester subagents
├─ .github/workflows/     CI: agent-config-sync, backend-tests, frontend-tests
├─ .githooks/pre-commit   blocks commits on main + runs the parity check
├─ scripts/               check_agent_config_sync.py (parity), seed.py
└─ docker-compose.yml     one-command local dev
```

---

## Documentation index

### Product & architecture

| Doc | What it is |
|---|---|
| [`mvp-spec.md`](mvp-spec.md) | **FROZEN v0 spec** — scope, prices, SKUs, data model, API, prompt/pricing rules, injection guards, unit economics. Do not contradict; do not edit for scope changes. |
| [`docs/architecture.md`](docs/architecture.md) | System context + container diagrams, container responsibilities, trust boundaries, in/out of v0, deployment shape. |
| [`docs/architecture-sequences.md`](docs/architecture-sequences.md) | Mermaid sequence for every v0 journey (sign-in, save rates, generate, edit, PDF, subscribe, regenerate) + the v1.1 competitor-upload ghost. Every LLM hop is marked "AI inference". |
| [`docs/ai-touchpoints.md`](docs/ai-touchpoints.md) | The authoritative table of **where the LLM is and is not called in v0** — event, path, LLM yes/no, quota yes/no, who computes money, failure behavior. |

### Decisions (ADRs)

| ADR | Decision |
|---|---|
| [`ADR-001`](docs/agents/adrs/ADR-001-supabase-jwt-verification.md) | FastAPI **only verifies** the Supabase JWT (JWKS / HS256 dev), provisions a local `users` row on first sight of a `sub`. No passlib / custom auth. |
| [`ADR-002`](docs/agents/adrs/ADR-002-model-choice-and-structured-output.md) | LLM = `claude-haiku-4-5` (config `AI_MODEL`), structured JSON via `messages.parse`, schema has **no money field**, cached system prompt, no streaming. Final pin from the §16 bake-off. |
| [`ADR-003`](docs/agents/adrs/ADR-003-optional-phone-otp-login.md) | Phone OTP is an **optional, feature-flagged** Supabase Auth method (`AUTH_PHONE_OTP`, default off). Supabase owns the SMS send; FastAPI still only verifies the JWT. |
| [`ADR-004`](docs/agents/adrs/ADR-004-auth-redirect-callback.md) | One Next.js `/auth/callback` route handler — every sign-in path funnels through it; it does a Supabase code-exchange + redirect only (no `/v1` call), always to `/` in v0. |

### Planning & process

| Doc | What it is |
|---|---|
| [`docs/roadmap.md`](docs/roadmap.md) | Deferred / not-v0 work — the only place new "later" ideas are recorded. |
| [`docs/NEXT-STEPS.md`](docs/NEXT-STEPS.md) | Current pre-launch checklist, blocking decisions (name collision, quota tiers, model pin), and the deferred-engineering queue. |
| [`docs/claude-implementation-waves.md`](docs/claude-implementation-waves.md) | The wave-by-wave build plan (Wave 1 architecture → 2 workflow/parity → 3 skeleton → 4 AI + PDF + Razorpay). |
| [`AGENTS.md`](AGENTS.md) | Repo map + where each tool's config lives + the enforced Cursor↔Claude sync rule. |
| [`CLAUDE.md`](CLAUDE.md) | Claude Code's project rules + the **Multi-agent workflow** + the **Cursor ↔ Claude Code parity table**. |
| [`backend/CLAUDE.md`](backend/CLAUDE.md) · [`frontend/CLAUDE.md`](frontend/CLAUDE.md) · [`docs/CLAUDE.md`](docs/CLAUDE.md) | Standing contracts for each area — conventions, boundaries, testing. Not status pages. |
| [`docs/agents/`](docs/agents) | Live workflow artifacts — `slices/`, `adrs/`, `test-plans/`, `test-reports/`, each with a `_TEMPLATE.md`. First worked example: [`S-000`](docs/agents/slices/S-000-agent-bootstrap.md). |
| [`scripts/check_agent_config_sync.py`](scripts/check_agent_config_sync.py) | Fails a commit/PR that edits one side of a Cursor↔Claude pair without the other (pre-commit hook + CI). |

---

## The build workflow

Every change goes through one cycle:

```
PM (slice brief) → Architect (tech spec) → Builder (code) → Tester (report) → PM (accept)
```

No Builder before the Architect has filled the slice's technical section against the Wave 1 diagrams.
Never commit on `main` — feature branch + PR. Full rules: [`CLAUDE.md`](CLAUDE.md) "Multi-agent workflow"
and [`.cursor/rules/agents/workflow.mdc`](.cursor/rules/agents/workflow.mdc).

One-time per clone: `git config core.hooksPath .githooks`

---

## v0 in one paragraph

Browser (Next.js, UI only) → FastAPI `/v1` (all business logic) → Supabase Auth (JWT verify),
Supabase Postgres, private Storage; Razorpay orders with HMAC-verified idempotent webhooks;
**one** LLM call behind a Python adapter, on `POST /v1/proposals` and
`POST /v1/proposals/{id}/regenerate` **only**. Prices are assembled in FastAPI from the user's saved
amounts *before* the model runs; any money the model returns is stripped. PATCH, PDF, download,
duplicate, checkout, and webhooks never call the LLM. Flutter and Stripe are out of the v0 picture.

**Auth (v0):** Supabase email/password (verified) + Google, both landing on `/auth/callback`
(ADR-004). Phone OTP is an optional method behind `AUTH_PHONE_OTP` / `NEXT_PUBLIC_AUTH_PHONE_OTP`
(default off, off in CI — S-005, ADR-003). No TOTP — see [`docs/roadmap.md`](docs/roadmap.md).

---

## Status

`main` — all 4 build waves plus the S-005 / S-006 pre-launch slices are merged.
Tests on `main`: **68 backend pytest + 30 frontend Jest**, `tsc` clean, `next build` green.
`AI_PROVIDER=mock` + `PAYMENTS_PROVIDER=mock` + stubbed SDKs are the CI default — **no live keys anywhere**.

| Wave | Deliverable | State |
|---|---|---|
| 1 | Architecture pack — `docs/architecture*.md`, `docs/ai-touchpoints.md` | **done** |
| 2 | Cursor↔Claude parity + PM→Architect→Builder→Tester cycle + roadmap seed (`S-000`) | **done** |
| 3 | Platform skeleton — Supabase JWT verify, `/v1/me`, proposals CRUD, PATCH allowlist, quota counter, mock adapters + Next.js client | **done** (`S-001` + `S-002`) |
| 4 | AI generate + regenerate + cached PDF + Razorpay | **done** (`S-003` + `S-004`) |
| — | Pre-launch hardening slices | `S-005` phone-OTP · `S-006` hosted checkout + `/auth/callback` |

| Slice | Phase | Status |
|---|---|---|
| [`S-000-agent-bootstrap`](docs/agents/slices/S-000-agent-bootstrap.md) | 0 Bootstrap | **Accepted** |
| [`S-001-platform-skeleton`](docs/agents/slices/S-001-platform-skeleton.md) | 1 Platform skeleton | **Accepted** — FastAPI `/v1`, mock adapters, Alembic |
| [`S-002-nextjs-client`](docs/agents/slices/S-002-nextjs-client.md) | 1 Platform skeleton | **Accepted** — Next.js 15 client, middleware guard, one API module |
| [`S-003-live-ai-and-pdf`](docs/agents/slices/S-003-live-ai-and-pdf.md) | 2 AI + money | **Accepted** — live Claude adapter (ADR-002) + server-side cached PDF |
| [`S-004-razorpay-and-web-money`](docs/agents/slices/S-004-razorpay-and-web-money.md) | 2 AI + money | **Accepted** — Razorpay Orders API + HMAC webhook + web PDF / upgrade wiring |
| [`S-005-phone-otp-login`](docs/agents/slices/S-005-phone-otp-login.md) | 1 auth (pre-launch) | **Accepted** — optional phone OTP behind `AUTH_PHONE_OTP` (default off, ADR-003); success funnels through `/auth/callback` |
| [`S-006-hosted-checkout`](docs/agents/slices/S-006-hosted-checkout.md) | 2 money (pre-launch) | **Accepted** — hosted Razorpay Checkout.js on `/billing` + Next.js `/auth/callback` code-exchange route (ADR-004); AC 2 / AC 12 keep a pre-launch live-key manual step |

**What's next:** signed storage URLs, the model bake-off + prompt-cache check, Playwright E2E, and
prod ops (secrets, monitoring, backups, deploy). Tracked in [`docs/NEXT-STEPS.md`](docs/NEXT-STEPS.md) §3.
Open decisions (name collision, quota micro-tier, `AI_MODEL` pin) and the Dependabot backlog are in §1–2.

`backend/` is the FastAPI service (auth, `/v1/me`, proposals CRUD + quota, live Claude adapter
`AI_PROVIDER=anthropic`, `reportlab` cached PDF watermarked on Free, live Razorpay rail
`PAYMENTS_PROVIDER=razorpay`). `frontend/` is the Next.js 15 client (Supabase auth + middleware guard,
one API module, sign-in / dashboard / settings / new-proposal / split editor / `/billing`) with real
PDF download and an upgrade → hosted Razorpay checkout flow.

---

## Run it

```bash
docker compose up --build
```

Backend `http://localhost:8000/docs` · Web `http://localhost:3000` (needs `NEXT_PUBLIC_SUPABASE_*`
set for auth). Without Docker:

```bash
# backend
cd backend && pip install -r requirements.txt && cp .env.example .env
PYTHONPATH=. python -m alembic upgrade head && PYTHONPATH=. python scripts/seed.py
PYTHONPATH=. uvicorn app.main:app --reload

# frontend (separate shell)
cd frontend && npm install && cp .env.example .env.local && npm run dev
```

Tests: `cd backend && PYTHONPATH=. python -m pytest -q` · `cd frontend && npm test`

## CI

Three GitHub Actions workflows gate every PR ([`.github/workflows/`](.github/workflows)):
`agent-config-sync` (Cursor↔Claude parity), `backend-tests` (pytest), `frontend-tests`
(Jest + `tsc` + `next build`). A CodeQL scan also runs. No workflow uses a live LLM or Razorpay key.
