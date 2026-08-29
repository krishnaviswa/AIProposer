# Documentation & spec rules

> Mirrors `.cursor/rules/docs-and-api.mdc` (Cursor `globs: README.md,docs/**/*,mvp-spec.md`). Keep
> both in sync — see the parity table in the root [`CLAUDE.md`](../CLAUDE.md).

## The documents and who may change them

| Document | Status | Who edits it |
|---|---|---|
| [`../mvp-spec.md`](../mvp-spec.md) | **FROZEN** | Nobody, for scope / price / SKU / count changes. Dated changelog entries only, after a human review. |
| [`architecture.md`](architecture.md) | Binding | **Architect**, when a slice changes containers, trust boundaries, or the in/out list. |
| [`architecture-sequences.md`](architecture-sequences.md) | Binding | **Architect**, when a slice adds or changes a v0 journey. Keep the "AI inference" note on every LLM hop. |
| [`ai-touchpoints.md`](ai-touchpoints.md) | Binding | **Architect**, when a slice touches an LLM / quota / money path. Must stay true: two v0 AI hops, nowhere else. |
| [`roadmap.md`](roadmap.md) | Living | Anyone, in the **same PR** as the idea. New "later" ideas land here — not in `mvp-spec.md`. |
| [`../README.md`](../README.md) | Index | Anyone, to keep links + the wave/slice status table current. |
| `agents/**` | Artifacts | The workflow roles, from `_TEMPLATE.md` files. Not prose docs. |

## Rules

- **Never add a new top-level prose `.md`.** Product decisions live in `mvp-spec.md` (frozen) + the
  three Wave 1 docs. Deferred ideas live in `docs/roadmap.md`. Everything else is an index link or an
  agent artifact.
- If a slice would contradict a Wave 1 doc, that is a red flag — raise it with Architect / PM. If the
  spec genuinely needs to change, stop and ask for a human review.
- Mermaid for non-trivial flows. `;` is a statement separator in mermaid — use `,` in message text.
- `.cursor/**`, `CLAUDE.md`, `.claude/**` are tooling config, exempt from the "no new prose doc" rule.
