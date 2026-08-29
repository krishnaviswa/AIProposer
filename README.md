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
| 3 | Platform skeleton — Supabase JWT verify, `/v1/me`, proposals CRUD, PATCH allowlist, quota counter, mock adapters (LLM dark) | **backend done (`S-001`)** · Next.js client → `S-002` |
| 4 | AI generate + regenerate + cached PDF + Razorpay | not started |

| Slice | Phase | Status |
|---|---|---|
| [`S-000-agent-bootstrap`](docs/agents/slices/S-000-agent-bootstrap.md) | 0 Bootstrap | **Accepted** |
| [`S-001-platform-skeleton`](docs/agents/slices/S-001-platform-skeleton.md) | 1 Platform skeleton | **Accepted** — FastAPI `/v1`, 42 tests |
| `S-002` — Next.js client | 1 Platform skeleton | not started |

`backend/` now holds the FastAPI skeleton (auth, `/v1/me`, proposals CRUD + quota, mock adapters,
Alembic, pytest). The **AI adapter is a deterministic mock** — `AI_PROVIDER != mock` fails at boot;
real inference + PDF + Razorpay are Wave 4. `frontend/` is still just its `CLAUDE.md` contract (`S-002`).

### Run the backend

```bash
docker compose up --build
```

or, without Docker:

```bash
cd backend && pip install -r requirements.txt && cp .env.example .env
PYTHONPATH=. python -m alembic upgrade head && PYTHONPATH=. python scripts/seed.py
PYTHONPATH=. uvicorn app.main:app --reload   # http://localhost:8000/docs
```

Tests: `cd backend && PYTHONPATH=. python -m pytest -q`
