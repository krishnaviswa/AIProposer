# AIProposer — Agent Guide

Single-operator AI proposal / quote generator. FastAPI backend, Next.js web client, Supabase Auth +
Postgres + Storage, Razorpay, one LLM adapter. India-first billing.

## Start here

| You need | Read |
|---|---|
| Frozen product scope, prices, SKUs, data model, API, prompt/pricing rules | [`mvp-spec.md`](mvp-spec.md) — **do not edit for scope changes** |
| System context, containers, trust boundaries | [`docs/architecture.md`](docs/architecture.md) |
| Every v0 user journey (mermaid) | [`docs/architecture-sequences.md`](docs/architecture-sequences.md) |
| Where the LLM is and is not called | [`docs/ai-touchpoints.md`](docs/ai-touchpoints.md) |
| Deferred / not-v0 work | [`docs/roadmap.md`](docs/roadmap.md) |
| The PM → Architect → Builder → Tester cycle | [`CLAUDE.md`](CLAUDE.md) "Multi-agent workflow" + `.cursor/rules/agents/workflow.mdc` |
| The wave-by-wave build plan | [`docs/claude-implementation-waves.md`](docs/claude-implementation-waves.md) |

## Layout

- `backend/` — FastAPI, `/v1` REST API, adapters, Alembic (created in Wave 3).
- `frontend/` — Next.js App Router web client (created in Wave 3).
- `docs/` — the three binding Wave 1 docs + `roadmap.md` + `agents/` workflow artifacts.
- `docs/agents/` — live artifacts: `slices/`, `adrs/`, `test-plans/`, `test-reports/` (each with `_TEMPLATE.md`).
- `.cursor/rules/` — Cursor rules, loaded by `alwaysApply` / `globs`.
- `CLAUDE.md` (root + nested `backend/`, `frontend/`, `docs/`) and `.claude/agents/` — Claude Code's
  equivalent, loaded by directory. Same conventions, same PM / Architect / Tester roles, so a session
  started in either tool knows what the other has done.
- `scripts/` — `check_agent_config_sync.py` (parity enforcement).

## Sync rule (enforced, not advisory)

This project is developed with **both Cursor and Claude Code**. When you change a convention in
`.cursor/rules/**`, port the same change to the matching `CLAUDE.md` / `.claude/agents/**` file **in
the same commit**, and vice versa. The exact file-to-file map is the parity table in the root
[`CLAUDE.md`](CLAUDE.md).

[`scripts/check_agent_config_sync.py`](scripts/check_agent_config_sync.py) fails if one side of a
pair changed without the other. It is wired as:

- a local pre-commit hook — `.githooks/pre-commit`, enable once with `git config core.hooksPath .githooks`
- a CI check — `.github/workflows/agent-config-sync.yml` (add it as a required status check in
  branch protection to make the rule non-bypassable)

## Local development

```bash
docker compose up --build
```

(Compose file arrives with the Wave 3 skeleton. Every adapter runs `mock` / local; no live LLM or
Razorpay keys, ever, in dev or CI.)

## Artifact templates

| Template | Path |
|---|---|
| Slice | [`docs/agents/slices/_TEMPLATE.md`](docs/agents/slices/_TEMPLATE.md) |
| ADR | [`docs/agents/adrs/_TEMPLATE.md`](docs/agents/adrs/_TEMPLATE.md) |
| Test plan | [`docs/agents/test-plans/_TEMPLATE.md`](docs/agents/test-plans/_TEMPLATE.md) |
| Test report | [`docs/agents/test-reports/_TEMPLATE.md`](docs/agents/test-reports/_TEMPLATE.md) |
| Worked example | [`docs/agents/slices/S-000-agent-bootstrap.md`](docs/agents/slices/S-000-agent-bootstrap.md) |

## Documentation rule

`mvp-spec.md` is frozen. The three `docs/architecture*.md` / `docs/ai-touchpoints.md` files are
binding and maintained by the Architect. New "later" ideas go in `docs/roadmap.md`. Do not add a new
top-level prose `.md`. `docs/agents/**` and `.cursor` / `.claude` config are exempt (artifacts / tooling).
