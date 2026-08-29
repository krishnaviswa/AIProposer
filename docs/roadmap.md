# AIProposer — Roadmap (deferred work)

**Status:** Wave 1 **stub**. Wave 2 seeds the full deferred list (Flutter, Stripe, packs, competitor
compare, infographics, seats, Hindi, TOTP, model bake-off, prompt cache, single-session, screenshot
teaser, Scale, …) with `status / target version / why not v0 / spec pointer` per row, and every new
"later" idea from chat lands here in the same PR.

Nothing here unfreezes [`../mvp-spec.md`](../mvp-spec.md).

| Item | Status | Target | Why not v0 | Spec pointer |
|---|---|---|---|---|
| **SMS / phone OTP auth rail (India +91)** | `blocked-on-decision` | TBD | AUTH OVERRIDE in the wave file was left unfilled; frozen spec ships email-verified + Google only. Needs a product decision before it can be scheduled. | `mvp-spec.md` §3.1, §13.1; [`architecture.md`](architecture.md#auth-override-recorded-once-here-waves-24-inherit-this) |
| Authenticator TOTP / MFA | deferred | post-v0 | Not in frozen scope; MEngPlat TOTP is explicitly *not* copied. | `mvp-spec.md` §18.2 |
| Everything else deferred | — | — | Seeded in Wave 2. | `mvp-spec.md` §3.2, §14 |
