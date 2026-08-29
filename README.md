# AIProposer

India-first, single-operator **quote / proposal generator**. A freelancer pastes a client brief,
confirms **their own** package prices or hourly rate, and leaves with a sendable proposal
(PDF-like preview + cached PDF) — not a chat transcript, not a JSON export.

> `AIProposer` is the internal git name only. Public product name and domain are deferred
> (there is a known name collision with a live product — see `mvp-spec.md` §14 and `docs/roadmap.md`).

---

## Documentation index

### Product & architecture

| Doc | What it is |
|---|---|
| [`mvp-spec.md`](mvp-spec.md) | **FROZEN v0 spec** — scope, prices, SKUs, data model, API, prompt/pricing rules, injection guards, unit economics. The source of truth. Do not contradict; do not edit for scope changes. |
| [`docs/architecture.md`](docs/architecture.md) | System context + container diagrams, container responsibilities, trust boundaries, in/out of v0, deployment shape. |
| [`docs/architecture-sequences.md`](docs/architecture-sequences.md) | Mermaid sequence for every v0 user journey (sign-in, save rates, generate, edit, PDF, subscribe, regenerate) + the v1.1 competitor-upload ghost. Every LLM hop is marked "AI inference". |
| [`docs/ai-touchpoints.md`](docs/ai-touchpoints.md) | The authoritative table of **where the LLM is and is not called in v0** — event, path, LLM yes/no, quota yes/no, who computes money, failure behavior. |
| [`docs/roadmap.md`](docs/roadmap.md) | Deferred / not-v0 work — the only place new "later" ideas are recorded. |

### How the repo is built

| Doc | What it is |
|---|---|
| [`AGENTS.md`](AGENTS.md) | Repo map + where each tool's config lives + the enforced Cursor↔Claude sync rule. |
| [`CLAUDE.md`](CLAUDE.md) | Claude Code's project rules + the **Multi-agent workflow** + the **Cursor ↔ Claude Code parity table**. |
| [`.cursor/rules/`](.cursor/rules) | Cursor's mirror of the same rules and roles. |
| [`docs/agents/`](docs/agents) | Live workflow artifacts — `slices/`, `adrs/`, `test-plans/`, `test-reports/`, each with a `_TEMPLATE.md`. First worked example: [`S-000-agent-bootstrap`](docs/agents/slices/S-000-agent-bootstrap.md). |
| [`scripts/check_agent_config_sync.py`](scripts/check_agent_config_sync.py) | Fails a commit/PR that edits one side of a Cursor↔Claude pair without the other (pre-commit hook + CI). |
| [`docs/claude-implementation-waves.md`](docs/claude-implementation-waves.md) | The wave-by-wave build plan (Wave 1 architecture → Wave 2 workflow/parity → Wave 3 skeleton → Wave 4 AI + PDF + Razorpay). |

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
Supabase Postgres, private Storage; Razorpay subscriptions with HMAC-verified idempotent webhooks;
**one** LLM call behind a Python adapter, on `POST /v1/proposals` and
`POST /v1/proposals/{id}/regenerate` **only**. Prices are assembled in FastAPI from the user's saved
amounts *before* the model runs; any money the model returns is stripped. PATCH, PDF, download,
duplicate, checkout, and webhooks never call the LLM. Flutter and Stripe are out of the v0 picture.

**Auth (v0):** Supabase email/password (verified) + Google. No SMS OTP, no TOTP — see
[`docs/roadmap.md`](docs/roadmap.md).

---

## Status

| Wave | Deliverable | State |
|---|---|---|
| 1 | Architecture pack — `docs/architecture*.md`, `docs/ai-touchpoints.md` | **done** |
| 2 | Cursor↔Claude parity + PM→Architect→Builder→Tester cycle + roadmap seed (`S-000`) | **done** |
| 3 | Platform skeleton — Supabase JWT verify, `/v1/me`, proposals CRUD, PATCH allowlist, quota counter, mock adapters (LLM dark) + Next.js client | **done (`S-001` backend + `S-002` web)** |
| 4 | AI generate + regenerate + cached PDF + Razorpay | **done (`S-003` live Claude + PDF · `S-004` Razorpay + web wiring)** |

| Slice | Phase | Status |
|---|---|---|
| [`S-000-agent-bootstrap`](docs/agents/slices/S-000-agent-bootstrap.md) | 0 Bootstrap | **Accepted** |
| [`S-001-platform-skeleton`](docs/agents/slices/S-001-platform-skeleton.md) | 1 Platform skeleton | **Accepted** — FastAPI `/v1`, 42 pytest tests |
| [`S-002-nextjs-client`](docs/agents/slices/S-002-nextjs-client.md) | 1 Platform skeleton | **Accepted** — Next.js 15 client, 8 Jest tests |
| [`S-003-live-ai-and-pdf`](docs/agents/slices/S-003-live-ai-and-pdf.md) | 2 AI + money | **Accepted** — live Claude adapter (ADR-002) + cached PDF, 56 pytest tests |
| [`S-004-razorpay-and-web-money`](docs/agents/slices/S-004-razorpay-and-web-money.md) | 2 AI + money | **Accepted** — Razorpay Orders API + HMAC webhook + web PDF/upgrade, 61 pytest + 12 Jest |
| [`S-006-hosted-checkout`](docs/agents/slices/S-006-hosted-checkout.md) | 2 AI + money | **Specified** — hosted Razorpay Checkout.js on `/billing` + Next.js `/auth/callback` code-exchange route (ADR-004); Builder pending |

`backend/` is the FastAPI service (auth, `/v1/me`, proposals CRUD + quota, Alembic, pytest) with a
**live Claude adapter** (`AI_PROVIDER=anthropic`, `claude-haiku-4-5` per ADR-002), a **server-side
cached PDF** (`reportlab`, watermarked on Free), and a **live Razorpay rail** (`PAYMENTS_PROVIDER=razorpay`
— Orders API + HMAC webhook). `AI_PROVIDER=mock` + `PAYMENTS_PROVIDER=mock` + stubbed SDKs stay the
default and the only thing CI runs — no live keys anywhere. `frontend/` is the Next.js 15 client
(Supabase auth + middleware guard, one API module, sign-in / dashboard / settings / new-proposal /
split editor / `/billing`, Jest) with real PDF download and an upgrade → Razorpay checkout flow.

**Wave 4 complete** — the two v0 AI hops, the cached PDF, and the Razorpay rail are all live behind
their adapters; `mock`/stub remain the default. Deferred finishing touches (hosted checkout.js,
signed storage URLs, the model bake-off) are in [`docs/roadmap.md`](docs/roadmap.md).

### Run it

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
