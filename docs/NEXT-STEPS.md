# AIProposer — Next Steps

_Last updated: 2026-08-29. All 4 implementation waves are complete and merged to `main` (PR #1, merge commit `75a0a0e`). ~73 tests green (61 backend pytest + 12 frontend Jest). Mock/stub adapters are the CI default; no live keys anywhere in CI._

## 1. Repo housekeeping

- [x] Sync local `main` to `origin/main` (`75a0a0e`) — done 2026-08-29.
- [x] Delete merged branches local + remote: `docs/claude-implementation-waves`, `wave-3-platform-skeleton`, `wave-4-live-ai-pdf-razorpay`, stray local `fix-` — done 2026-08-29. Only `main` + the Dependabot branch remain.
- [x] `README.md` — already rewritten during the wave work (accurate FastAPI + Next.js stack, `docker compose up --build`). NEXT-STEPS's earlier "still a stub" note was from the pre-sync snapshot; no longer true.
- [ ] Disable the environment's auto-commit/auto-push tool so slice-cycle commits stay deliberate (it committed `3ae31f7` mid-edit with a wrong message). **External tool — user must do this.**
- [ ] Triage Dependabot: GitHub reports 44 vulnerabilities on `main` (2 critical, 16 high) and an open `dependabot/npm_and_yarn/frontend/...` PR branch. Review + merge or dismiss.

## 2. Blocking decisions (need the user)

- [ ] **Name collision** — `AIProposer` clashes with the live product at aiproposer.com (Upwork bid-letter tool). User confirmed unintentional. Pick a new name/domain before any launch, branding, or marketing work.
- [x] **Auth scope** — decision 2026-08-29: **add phone OTP as an optional login method.** Built as
  slice **S-005** (`docs/agents/slices/S-005-phone-otp-login.md`, ADR-003-optional-phone-otp-login) —
  feature-flagged `AUTH_PHONE_OTP` (default off, off in CI), phone-only accounts allowed, MSG91 as the
  +91 SMS provider, `mvp-spec.md` untouched (roadmap row `blocked-on-decision` → `feature-flag`).
  Still open before turning it on in prod: MSG91 account + DLT sender-ID registration.
- [ ] **Quota tiers** — gap between Free (3/mo) and Starter (20/mo). Decide whether to add a ~15/mo micro-tier.
- [ ] **Model pin** — `AI_MODEL` defaults to `claude-haiku-4-5` (meets mvp-spec §4 ≤ $0.012/proposal). Final pin is supposed to come from the §16 20-brief benchmark (see below).

## 3. Pre-launch engineering (deferred from the waves)

- [x] Hosted Razorpay checkout — `checkout.js` on `/billing` via `next/script` + Next.js `/auth/callback` code-exchange route. **Slice S-006** (`docs/agents/slices/S-006-hosted-checkout.md`, ADR-004) — Accepted 2026-08-30, merged to `main` (PR #3). Real Razorpay modal + real Supabase OAuth stay pre-launch manual checks (M-004 / M-005).
- [ ] Signed storage URLs — S3 / Supabase Storage signed URLs for PDF delivery (today the PDF is served straight from the backend).
- [ ] Model bake-off — run the mvp-spec §16 20-brief benchmark across candidate models; verify prompt-cache hit rate on the cached system prompt; pin `AI_MODEL`.
- [ ] Playwright E2E — end-to-end coverage of the sign-in → new proposal → edit → PDF → upgrade flow. Only unit/integration tests exist now.
- [ ] Ops readiness — production env config, secrets management, error monitoring/alerting, DB backups, deploy pipeline.

## 4. v1.1+ roadmap (post-launch, not scoped)

Competitor-compare view · one-page infographic export · Flutter mobile app · Stripe as second payment provider · team seats · Hindi output (revisit at v1.2 on demand signal) · proposal template packs.

## Reference

- Frozen spec: `mvp-spec.md` (§13 answers, §14 revisions, §16 benchmark plan)
- Architecture: `docs/architecture.md`, `docs/architecture-sequences.md`, `docs/ai-touchpoints.md`
- Slice history: `docs/agents/slices/` (S-000 … S-004 Accepted; S-006 hosted-checkout Accepted + merged; S-005 phone-OTP Accepted)
