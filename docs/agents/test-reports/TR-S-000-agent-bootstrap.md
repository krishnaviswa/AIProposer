# TR-S-000: Agent workflow + parity bootstrap — Test report

| Field | Value |
|---|---|
| **Slice** | S-000 |
| **Author** | Tester |
| **Date** | 2026-08-29 |
| **Recommendation** | **Ship** |

---

## Summary

All 10 acceptance criteria pass. The parity script fails a one-sided pair edit (naming the exact
mirror file to update) and passes a two-sided edit, in both `--staged` and `--range` modes. The
local pre-commit hook aborts a real one-sided commit and its branch guard refuses `main`/`master`.
The CI workflow is wired to `pull_request` (not dispatch-only). All four artifact templates exist,
the parity table and `SYNC_GROUPS` match with no ghost paths, the README links every required doc,
and `docs/roadmap.md` has all 15 seeded rows. No product code touched — `docs/ai-touchpoints.md`
is unchanged and still accurate (zero AI hops in this slice).

---

## AC coverage matrix

| AC# | Description | Type | Test reference | Result |
|---|---|---|---|---|
| 1 | One-sided staged pair edit → script exits 1, names the mirror | M | M-001 (live: staged `role-tester.mdc` only → `exit 1`, "Also update: `.claude/agents/tester.md`") | Pass |
| 2 | Both sides staged → script exits 0 | M | M-002 (live: staged both → `exit 0`, "in sync") | Pass |
| 3 | CI runs the check on PRs via `--range` | M | M-003 (`agent-config-sync.yml`: `on: pull_request` + `--range "<base>...<head>"` step, triggers not commented) | Pass |
| 4 | Hook refuses commits on `main`/`master` | M | M-004 (`.githooks/pre-commit`: `[ "$branch" = "main" ] ... exit 1` before any staging work) | Pass |
| 5 | Hook blocks a one-sided edit; no commit lands | M | M-005 (live: enabled hook, staged `project.mdc` only, `git commit` → sync failure printed, `git log` shows HEAD still `3ae31f7`, message absent) | Pass |
| 6 | A `_TEMPLATE.md` for slices / adrs / test-plans / test-reports | M | M-006 (all 4 present) | Pass |
| 7 | Parity table ⇄ `SYNC_GROUPS`, no drift | M | M-007 (every `.cursor/rules/**.mdc` is in a group; every group path exists; table `.mdc` set == group `.mdc` set) | Pass |
| 8 | README links spec + 3 Wave 1 docs + `AGENTS.md` + `CLAUDE.md` + `docs/agents/` + roadmap + waves file | M | M-008 (all 9 link targets present) | Pass |
| 9 | Roadmap seeded: Flutter, Stripe, packs, competitor compare, infographics, seats, Hindi, TOTP, SMS OTP, public name, model bake-off, single-session, prompt cache, screenshot teaser, Scale | M | M-009 (all 15 rows present with status / target / why-not-v0 / spec pointer) | Pass |
| 10 | Each `.claude/agents/*.md` has `name`/`description`/`tools` frontmatter + a parity pointer | M | M-010 (product-manager, architect, tester — all pass) | Pass |

**Coverage:** 10 / 10 AC mapped.

---

## Backend tests

None — this slice has no backend code.

---

## Frontend tests

None — this slice has no frontend code.

---

## Manual / integration

| ID | Check | Result |
|---|---|---|
| M-001 | `python scripts/check_agent_config_sync.py --staged` with one side of a pair staged | Pass — `exit 1`, names `.claude/agents/tester.md` |
| M-002 | same with both sides staged | Pass — `exit 0` |
| M-003 | Read `.github/workflows/agent-config-sync.yml` | Pass — `pull_request` + `push: [main]` + `workflow_dispatch`; `--range` step present |
| M-004 | Read `.githooks/pre-commit` branch guard | Pass |
| M-005 | Enable hook, attempt a one-sided commit on the feature branch | Pass — commit aborted, no new SHA |
| M-006 | `docs/agents/{slices,adrs,test-plans,test-reports}/_TEMPLATE.md` | Pass — 4/4 |
| M-007 | Consistency script (parity table ⇄ SYNC_GROUPS ⇄ files on disk) | Pass |
| M-008 | README link grep | Pass — 9/9 |
| M-009 | Roadmap seeded-item grep | Pass — 15/15 |
| M-010 | Agent-file frontmatter + parity line | Pass — 3/3 |
| M-011 | Mermaid in the S-000 slice + slice template parses (`mermaid.parse`) | Pass — 2/2 |
| M-012 | `--range` mode on commit `c19da23...3ae31f7` (both halves of every pair added) | Pass — `exit 0` |

Test markers appended during M-001/M-002/M-005 were reverted (`git checkout --`); working tree clean
apart from this slice's own artifacts.

---

## Regressions

None. No existing file's behavior changed; Wave 1 docs untouched except the README index and the
already-committed mermaid fix.

---

## Gaps / rework items

None blocking. Non-blocking notes for later:

1. The CI job only becomes a true merge gate once added as a **required status check** in GitHub
   branch protection (a Settings action, outside the repo). Recorded in `AGENTS.md` and the slice risks.
2. `--no-verify` bypasses the local hook by design; branch protection is the real lock.
3. `backend/app/models/` and `backend/app/services/` nested `CLAUDE.md` mirrors are intentionally
   deferred to Wave 3 — tracked in `docs/roadmap.md`.

---

## Sign-off

- [x] All AC mapped to tests (A or M)
- [x] Auth / ownership — N/A (no HTTP surface), stated
- [x] Money invariant — N/A (no pricing path), stated
- [x] `docs/ai-touchpoints.md` still matches the code (zero AI hops in this slice)
- [x] Ready for PM acceptance
