# ADR-002: Claude model, structured output, and "money never in the schema"

| Field | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-08-29 |
| **Slice** | S-003 |

---

## Context

Wave 4 turns on the two v0 AI hops (`POST /v1/proposals`, `.../regenerate`). We need a concrete
model, a structured-output mechanism, and a guarantee that the model cannot set prices
(`mvp-spec.md` §0.3, §9, §16).

Tensions:

- `mvp-spec.md` §4 sets a hard cost target — **≤ $0.012 (≈ ₹1.2) per generate** — and §13.3 says
  "benchmark 3 **mid-tier** models, pin, swap behind FastAPI". §4 also caps output at **2,000 tokens**
  and wants the system prompt **prompt-cached**.
- Anthropic's default guidance is "use the most capable model unless told otherwise" (Opus-tier).
  At ~1k system + ~1k input + 2k output, Opus 5 ($5/$25 per MTok) ≈ $0.06/generate — **5× over the
  spec target**. Sonnet 5 ($2/$10) ≈ $0.024 — 2× over.
- The frozen spec is the product owner's explicit instruction for this project; it names the tier
  and the ceiling.

---

## Decision

1. **Model is config (`AI_MODEL`), default `claude-haiku-4-5`.** Haiku 4.5 ($1/$5 per MTok) lands a
   full generate around **$0.004–$0.011** — inside the §4 target — and is a "mid-tier" pick. The
   adapter works with any Claude model; the final choice comes from the §16 ~20-brief benchmark
   (`docs/roadmap.md` → "model bake-off"). Do **not** hardcode a model in the adapter.
2. **Structured output via `client.messages.parse(output_format=…)`** (Anthropic SDK) against a
   Pydantic schema. Non-streaming (`mvp-spec.md` §4). `max_tokens = AI_MAX_TOKENS` (2000).
3. **The output schema has no money field.** `pricing` in the schema is `[{label, justification}]` —
   there is no `amount` / `price` / `currency` key anywhere in it, so a valid structured response
   *cannot contain a number the server would have to strip*. `services/generation` still builds the
   final `proposal_json.pricing` from the **assembler** (`amount_minor` + `currency` server-side) and
   only takes `justification` from the model, keyed by label.
4. **System prompt is stable and cached.** No timestamps, no per-request ids; sent as a single
   `system` block with `cache_control: {type: "ephemeral"}`. (For a ~1k-token prompt, caching may
   not engage on every model — harmless when it doesn't.)
5. **Failure = `AIGenerationError` → `502`, 0 quota, nothing persisted.** `stop_reason` of `refusal`
   or `max_tokens`, a `None` parsed output, or any `anthropic.APIError` all map to it. SDK
   `max_retries=1` (no retry storm, `mvp-spec.md` §16).
6. **Ingress guards unchanged** — `services/ingress.scrub()` runs before the call; the system prompt
   also instructs the model to ignore brief-embedded instructions (§16).

---

## Consequences

### Positive

- Meets the §4 cost target out of the box; swapping models is one env var.
- Money genuinely cannot originate in the model — it's a *structural* property of the schema, not a
  post-hoc filter. The strip step becomes a defence-in-depth no-op.
- `parse()` gives validated Pydantic objects; unknown keys are rejected by the schema.

### Negative / tradeoffs

- Haiku 4.5 is less capable than Sonnet/Opus at long-form persuasive copy. Acceptable for v0 — the
  benchmark will confirm or replace it, and "fewer included units assumes a high quality bar"
  (`mvp-spec.md` §11) so the pin matters.
- `parse()` is an SDK helper (`anthropic` 1.x); pinned in `requirements.txt`.
- Prompt caching on a ~1k-token prompt is model-dependent; we accept "cache when the provider allows".

### Follow-ups

- `docs/roadmap.md` "model bake-off" is the benchmark task (already listed).
- Wave 1 docs: no change — `ai-touchpoints.md` and sequence 3/7 already describe exactly this hop;
  only the Wave 3 "mock stands in" build note in `architecture-sequences.md` is updated.

---

## Alternatives considered

1. **Opus 5 / Sonnet 5 default.** Rejected — 2–5× over the frozen §4 cost target. Available via
   `AI_MODEL` for anyone who accepts the cost.
2. **Schema with an `amount` field + strip it server-side.** Rejected — leaves a window where a bug
   in the strip step ships model-invented money. No-field is strictly safer.
3. **Raw `output_config.format` + manual `json.loads`.** Works, but `parse()` is the documented
   recommended path and gives typed objects for free.
4. **Tool-use for structure.** More moving parts than `output_format` for a single fixed shape.
