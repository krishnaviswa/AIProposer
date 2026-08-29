#!/usr/bin/env python3
"""Enforce that Cursor rules (.cursor/rules/**) and their Claude Code mirrors
(CLAUDE.md files + .claude/agents/**) change together.

Each entry in SYNC_GROUPS is a set of files that describe the *same* convention
in two tools. If a commit / PR touches one file in a group without touching at
least one other file in that group, the pairing is out of sync and the check
fails. See the parity table in the root CLAUDE.md for what mirrors what.

Usage:
  python scripts/check_agent_config_sync.py --staged           # pre-commit
  python scripts/check_agent_config_sync.py --range A...B       # CI / PR diff
"""
from __future__ import annotations

import argparse
import subprocess
import sys

# Keep in lockstep with the parity table in the root CLAUDE.md.
# When the repo grows nested backend/frontend code (Wave 3), split
# backend/CLAUDE.md into app/models/ + app/services/ mirrors and add
# those groups here and to the parity table.
SYNC_GROUPS: list[set[str]] = [
    {".cursor/rules/project.mdc", "CLAUDE.md"},
    {".cursor/rules/agents/workflow.mdc", "CLAUDE.md"},
    {".cursor/rules/agents/role-product-manager.mdc", ".claude/agents/product-manager.md"},
    {".cursor/rules/agents/role-architect.mdc", ".claude/agents/architect.md"},
    {".cursor/rules/agents/role-tester.mdc", ".claude/agents/tester.md"},
    {".cursor/rules/backend-fastapi.mdc", "backend/CLAUDE.md"},
    {".cursor/rules/frontend-nextjs.mdc", "frontend/CLAUDE.md"},
    {".cursor/rules/testing.mdc", "backend/CLAUDE.md", "frontend/CLAUDE.md"},
    {".cursor/rules/docs-and-api.mdc", "docs/CLAUDE.md"},
]


def changed_files(args: argparse.Namespace) -> set[str]:
    if args.staged:
        cmd = ["git", "diff", "--cached", "--name-only"]
    else:
        cmd = ["git", "diff", "--name-only", args.range]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return {line.strip().replace("\\", "/") for line in result.stdout.splitlines() if line.strip()}


def find_problems(changed: set[str]) -> list[tuple[set[str], set[str]]]:
    problems = []
    for group in SYNC_GROUPS:
        touched = group & changed
        if touched and touched != group:
            problems.append((touched, group - touched))
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--staged", action="store_true", help="check staged changes (pre-commit)")
    source.add_argument("--range", help="git diff range, e.g. origin/main...HEAD (CI)")
    args = parser.parse_args()

    changed = changed_files(args)
    problems = find_problems(changed)

    if not problems:
        print("agent-config-sync: .cursor/rules and CLAUDE.md/.claude/agents are in sync.")
        return 0

    print("agent-config-sync: Cursor and Claude Code config changed out of sync.\n")
    for touched, missing in problems:
        print(f"  Changed:     {', '.join(sorted(touched))}")
        print(f"  Also update: {', '.join(sorted(missing))}\n")
    print(
        "Port the convention change to the other tool's file(s) too (see the parity\n"
        "table in the root CLAUDE.md). If this pair no longer mirrors 1:1, update\n"
        "SYNC_GROUPS in scripts/check_agent_config_sync.py and the parity table so\n"
        "this check stays accurate."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
