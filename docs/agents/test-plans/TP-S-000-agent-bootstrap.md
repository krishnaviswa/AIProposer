# TP-S-000: Agent workflow + parity bootstrap — Test plan

| Field | Value |
|---|---|
| **Slice** | S-000 |
| **Author** | Tester |
| **Date** | 2026-08-29 |

---

## Scope

Verify the parity-enforcement machinery and workflow scaffolding — no product code. Everything here
is checked by running the script / inspecting files; there is no running app.

---

## Test strategy

| Layer | Tool | Focus |
|---|---|---|
| Sync script | `python scripts/check_agent_config_sync.py` on real staged / range diffs | one-sided edit fails, two-sided passes, names the right mirror |
| Local hook | `sh .githooks/pre-commit` + a real `git commit` attempt | blocks a one-sided edit; refuses `main` |
| Static | file inspection + a small consistency script | templates exist, parity table ⇄ SYNC_GROUPS, README links, roadmap rows, agent frontmatter |
| CI | read `.github/workflows/agent-config-sync.yml` | wired to `pull_request` (not dispatch-only) |

No vendors, no network.

---

## AC → planned tests

| AC# | Approach | Test ID |
|---|---|---|
| 1 | Manual — stage one side of a pair, run `--staged`, expect exit 1 + names mirror | M-001 |
| 2 | Manual — stage both sides, run `--staged`, expect exit 0 | M-002 |
| 3 | Manual — read the workflow YAML for a `pull_request` trigger + `--range` step | M-003 |
| 4 | Manual — read hook; branch-guard logic refuses `main`/`master` | M-004 |
| 5 | Manual — enable hook, stage one-sided edit, `git commit`, expect abort + no new commit | M-005 |
| 6 | Manual — `ls docs/agents/*/_TEMPLATE.md` → 4 files | M-006 |
| 7 | Manual — consistency script: every `.mdc` in a SYNC_GROUP; parity table rows == groups | M-007 |
| 8 | Manual — grep README for all required links | M-008 |
| 9 | Manual — grep roadmap for the 15 seeded items | M-009 |
| 10 | Manual — each `.claude/agents/*.md` has `name`/`description`/`tools` + a Parity line | M-010 |

---

## Manual checklist

- [ ] M-001 one-sided `--staged` → exit 1, names the mirror
- [ ] M-002 two-sided `--staged` → exit 0
- [ ] M-003 CI on `pull_request` with `--range`
- [ ] M-004 hook refuses `main`/`master`
- [ ] M-005 real commit of a one-sided edit is aborted
- [ ] M-006 four `_TEMPLATE.md` files
- [ ] M-007 parity table ⇄ SYNC_GROUPS, no ghost paths
- [ ] M-008 README links spec + 3 Wave 1 docs + AGENTS.md + CLAUDE.md + docs/agents/ + roadmap + waves file
- [ ] M-009 roadmap seeded rows
- [ ] M-010 agent-file frontmatter + parity pointer

---

## Environment notes

Windows, Git Bash, Python 3.12. `.gitattributes` forces LF on the hook/script so `sh` runs them.
