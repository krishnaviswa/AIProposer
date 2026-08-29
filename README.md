# AIProposer

India-first, single-operator **quote / proposal generator**. A freelancer pastes a client brief,
confirms **their own** package prices or hourly rate, and leaves with a sendable proposal
(PDF-like preview + cached PDF) — not a chat transcript, not a JSON export.

> `AIProposer` is the internal git name only. Public product name and domain are deferred
> (there is a known name collision with a live product — see `mvp-spec.md` §14).

---

## Documentation index

| Doc | What it is |
|---|---|
| [`mvp-spec.md`](mvp-spec.md) | **FROZEN v0 spec** — scope, prices, SKUs, data model, API, prompt/pricing rules, injection guards, unit economics. The source of truth. Do not contradict. |
| [`docs/architecture.md`](docs/architecture.md) | System context + container diagrams, container responsibilities, trust boundaries, in/out of v0, deployment shape. |
| [`docs/architecture-sequences.md`](docs/architecture-sequences.md) | Mermaid sequence for every v0 user journey (sign-in, save rates, generate, edit, PDF, subscribe, regenerate) + the v1.1 competitor-upload ghost. Every LLM hop is marked "AI inference". |
| [`docs/ai-touchpoints.md`](docs/ai-touchpoints.md) | The authoritative table of **where the LLM is and is not called in v0** — event, path, LLM yes/no, quota yes/no, who computes money, failure behavior. |
| [`docs/roadmap.md`](docs/roadmap.md) | Deferred work. **Stub** — Wave 2 seeds the full list. |
| [`docs/claude-implementation-waves.md`](docs/claude-implementation-waves.md) | The wave-by-wave build plan (Wave 1 architecture → Wave 2 agent workflow/parity → Wave 3 skeleton → Wave 4 AI + PDF + Razorpay). |

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
| 1 | Architecture pack (this) | **done** |
| 2 | Cursor↔Claude parity + PM→Architect→Builder→Tester cycle + roadmap seed | not started |
| 3 | Platform skeleton — auth, CRUD, quotas, mock adapters (LLM dark) | not started |
| 4 | AI generate + regenerate + cached PDF + Razorpay | not started |

No application code yet — Wave 1 is documentation only.
