# AIProposer

Single-operator AI proposal / quote generator. One freelancer pastes a client brief, confirms
**their own** prices, and leaves with a sendable proposal (preview + cached PDF).

> This file is the Claude Code equivalent of `.cursor/rules/project.mdc` (Cursor's
> `alwaysApply: true` rule) plus the multi-agent workflow. Kept in sync with `.cursor/rules/` —
> see **Cursor ↔ Claude Code parity** at the bottom.

## Stack (v0)

- Backend: **FastAPI**, base path `/v1`. All business logic. Async SQLAlchemy + Alembic, Pydantic.
- Web: **Next.js** (App Router, TS, Tailwind) in `frontend/`. UI only — talks to FastAPI, nothing else.
- Identity: **Supabase Auth** (email verified + Google). FastAPI **only verifies** the JWT (JWKS).
- Data: Supabase **Postgres**; private **Storage** (signed short-TTL URLs).
- Payments: **Razorpay** only (INR rail). HMAC webhook + `WebhookEvents` idempotency.
- LLM: **one** provider behind a Python adapter. PDF: server-side from structured data.
- Adapters (AI / payments / storage / email) follow the **MEngPlat skeleton** — each has a `mock` used in CI.

## Source of truth

- [`mvp-spec.md`](mvp-spec.md) — **FROZEN v0 spec**. Never edit for scope / price / SKU / count changes.
  New "later" ideas → [`docs/roadmap.md`](docs/roadmap.md).
- [`docs/architecture.md`](docs/architecture.md) · [`docs/architecture-sequences.md`](docs/architecture-sequences.md)
  · [`docs/ai-touchpoints.md`](docs/ai-touchpoints.md) — **binding** Wave 1 pictures. Architect keeps them
  current; Builder does not contradict them.
- [`README.md`](README.md) is an index. [`AGENTS.md`](AGENTS.md) is the repo map.

## Non-negotiables

1. **Money on the proposal comes from the user.** Never from the model, never a multiplier. FastAPI
   strips/overwrites any amount the model emits (spec §0.3, §9).
2. **The LLM runs at exactly two v0 endpoints** — `POST /v1/proposals` and
   `POST /v1/proposals/{id}/regenerate`. Nowhere else ([`docs/ai-touchpoints.md`](docs/ai-touchpoints.md)). No streaming.
3. **`proposal_json` is server-only.** Clients get a **view DTO**. No "Export JSON" (spec §0.4, §15).
4. Use the **adapter layers**; `mock` in CI.
5. Business logic in FastAPI `services/`, not routers, never in Next.js route handlers.
6. REST under `/v1`. Supabase JWT verified in FastAPI — **no passlib / custom auth** (spec §18.2).
7. **Alembic migrations only** — no `create_all` in prod.
8. The client brief is **untrusted input** — char caps + injection guards before the model (spec §16).
9. Never commit secrets. No live LLM or Razorpay keys in CI.
10. Keep diffs minimal. Local dev: `docker compose up --build`.
11. Claude Code subagents (`product-manager`, `architect`, `tester`, `Explore`, `Plan`, any type)
    must be launched with `model: "sonnet"` explicitly. **Claude Code-specific** — a deliberate
    exception to the parity-sync rule; do **not** port this into any `.cursor/rules/` file.

## Auth model

One user role: the freelancer who **owns** the quote. Every `/v1` handler authorizes the caller for
**their own rows only** (`proposal.user_id == sub`). No `customer` / `merchant` / `admin` tiers;
seats are post-v0 ([`docs/roadmap.md`](docs/roadmap.md)).

## Multi-agent workflow

Mirrors `.cursor/rules/agents/workflow.mdc`. Sequence (mandatory):

```
PM (slice brief) → Architect (tech spec) → Builder (code) → Tester (report) → PM (accept)
```

Do not skip steps. **No Builder before the Architect has filled the slice's technical section and
checked it against the Wave 1 diagrams** (`docs/architecture-sequences.md`, `docs/ai-touchpoints.md`).

Roles are subagents in `.claude/agents/` (`product-manager.md`, `architect.md`, `tester.md`) —
invoke explicitly, e.g. *"Act as Product Manager for slice S-00X"*, or the Agent tool with
`subagent_type: architect` (always `model: "sonnet"`).

### Slice phases

- **Phase 0** — `S-000-agent-bootstrap`: the workflow itself, no product code.
- **Phase 1 — Platform skeleton** (Wave 3): Supabase JWT verify, `/v1/me`, proposals CRUD, PATCH
  allowlist, quota counter, mock adapters; LLM adapter returns mock copy or is unplugged.
- **Phase 2 — AI + money** (Wave 4): real LLM adapter, generate + regenerate, cached PDF, Razorpay.
- **Phase 3 — v1.1**: competitor compare (Pro+), infographics, packs.

### Definition of done (full cycle)

- [ ] All acceptance criteria numbered and testable
- [ ] Architect checklist complete on the slice; no contradiction with the Wave 1 docs
- [ ] Code on a **feature branch** + PR — never commit on `main` (`.githooks/pre-commit` enforces locally)
- [ ] Every AC mapped to a test (A or M) in the test report
- [ ] `docs/ai-touchpoints.md` still accurate if an LLM / quota / money / DTO path changed
- [ ] `docs/architecture-sequences.md` updated if a v0 journey changed
- [ ] New deferred ideas in `docs/roadmap.md` (same PR); `mvp-spec.md` untouched
- [ ] `README.md` wave/slice status table updated
- [ ] Parity check passes (`scripts/check_agent_config_sync.py`)
- [ ] PM set `Status: Accepted` on the slice file

### Cursor parity

Keep this "Multi-agent workflow" section and `.cursor/rules/agents/workflow.mdc` in sync (enforced
by `scripts/check_agent_config_sync.py`).

## Cursor ↔ Claude Code parity

This project is built with both Cursor and Claude Code. Every rule in `.cursor/rules/` has a mirror
in Claude Code's native config:

| This Cursor rule | Mirrors |
| --- | --- |
| `project.mdc` (stack / source of truth / non-negotiables) | `CLAUDE.md` (root) |
| `agents/workflow.mdc` | "Multi-agent workflow" section of `CLAUDE.md` (root) |
| `agents/role-product-manager.mdc` | `.claude/agents/product-manager.md` |
| `agents/role-architect.mdc` | `.claude/agents/architect.md` |
| `agents/role-tester.mdc` | `.claude/agents/tester.md` |
| `backend-fastapi.mdc` | `backend/CLAUDE.md` |
| `frontend-nextjs.mdc` | `frontend/CLAUDE.md` |
| `testing.mdc` | "Testing" section of `backend/CLAUDE.md` + `frontend/CLAUDE.md` |
| `docs-and-api.mdc` | `docs/CLAUDE.md` |

**Sync rule:** change a convention on one side, port it to the matching file in the **same commit**.
Enforced by [`scripts/check_agent_config_sync.py`](scripts/check_agent_config_sync.py) (pre-commit + CI).
If a pair stops mirroring 1:1, update `SYNC_GROUPS` in that script **and** this table.
