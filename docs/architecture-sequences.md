# AIProposer — Architecture sequences (v0)

**Status:** Wave 1 deliverable. Binding for Waves 2–4.
**Companion docs:** [`architecture.md`](architecture.md) · [`ai-touchpoints.md`](ai-touchpoints.md) · [`../mvp-spec.md`](../mvp-spec.md) (FROZEN)

Every diagram below is a v0 user journey. **Every LLM hop carries a `Note` reading "AI inference".**
If a diagram shows the LLM anywhere other than sequences 3 and 7, it is wrong (`mvp-spec.md` §9, §16;
see the v0 AI allowlist in [`ai-touchpoints.md`](ai-touchpoints.md)).

Participant legend: **U** freelancer (browser) · **W** Next.js · **A** FastAPI `/v1` ·
**Auth** Supabase Auth · **DB** Postgres · **LLM** LLM adapter · **S** private storage · **Pay** Razorpay.

> **Build note:**
> - **Wave 3 (S-001/S-002):** wired with the LLM adapter as a deterministic `MockAIProvider` and
>   `pdf_url` stubbed — zero production AI hop.
> - **Wave 4 (S-003):** the real Claude adapter (`AI_PROVIDER=anthropic`, ADR-002) is live at
>   sequences 3 & 7; sequence 5 now renders a real cached PDF (`reportlab`, watermark on Free,
>   invalidated by PATCH). `mock` / stub remain the default and the only thing CI exercises.
>   `AI_PROVIDER` and `PAYMENTS_PROVIDER` still validate at boot. `ai-touchpoints.md` is unchanged —
>   the two AI hops and their rules are exactly as drawn.

---

## 1. Sign in → JWT on the API

Per the AUTH OVERRIDE recorded in [`architecture.md`](architecture.md#auth-override-recorded-once-here-waves-24-inherit-this):
**email/password (verified) + Google.** Phone OTP is an optional method behind `AUTH_PHONE_OTP`
(default off, off in CI — S-005, ADR-003). No TOTP in v0.

Every sign-in path (Google OAuth, the email-verification link, email/password, **and** phone OTP when
`AUTH_PHONE_OTP` is enabled) funnels through one Next.js `/auth/callback` route handler (S-006,
[`ADR-004`](agents/adrs/ADR-004-auth-redirect-callback.md)). That handler does exactly two things — a
Supabase `exchangeCodeForSession` when a `?code=` is present, then an HTTP redirect — **no `/v1` call,
no domain logic.** v0 always redirects to `/` (no `next` / `redirectTo` param). A `?error=` param or a
failed exchange redirects to `/sign-in?error=…` with no session set.

```mermaid
sequenceDiagram
    actor U as Freelancer
    participant W as Next.js
    participant CB as Next.js /auth/callback route handler
    participant Auth as Supabase Auth
    participant A as FastAPI /v1

    Note over U,CB: Every sign-in path funnels through /auth/callback. The handler does ONLY a Supabase code exchange plus an HTTP redirect, no /v1 call, no domain logic.
    alt Email + password
        U->>W: email + password
        W->>Auth: signInWithPassword
        Auth-->>W: session (only if email is verified)
        W->>CB: hard nav to /auth/callback (no code, session cookie present)
    else Google OAuth
        U->>W: "Continue with Google"
        W->>Auth: signInWithOAuth(google, redirectTo = <origin>/auth/callback)
        Auth-->>CB: redirect to /auth/callback?code=...
    else Email verification link
        U->>CB: /auth/callback?code=... (from the email)
    else Phone OTP — only when AUTH_PHONE_OTP is enabled
        U->>W: phone number
        W->>Auth: signInWithOtp({ phone })
        Auth-->>U: SMS code (Supabase SMS provider, MSG91 for +91)
        U->>W: 6-digit code
        W->>Auth: verifyOtp({ phone, token })
        Auth-->>W: session (phone claim, email claim may be absent)
        W->>CB: hard nav to /auth/callback (no code, session cookie present)
    end

    opt ?code= present
        CB->>Auth: exchangeCodeForSession(code)
    end
    alt ?error= present, or the exchange fails
        CB-->>U: 303 /sign-in?error=<message>  (no session set)
    else exchange ok, or a valid session already present
        CB-->>U: 303 /  + Set-Cookie session
    end

    Note over W,A: v0 always redirects to /. No next / redirectTo param is read or supported (deep-link-back is a roadmap item). No LLM. No quota.
    U->>W: opens app / triggers any /v1 call
    W->>A: GET /v1/me  (Authorization: Bearer <JWT>)
    A->>Auth: fetch JWKS (cached)
    A->>A: verify signature + exp + aud, take sub as user_id
    alt valid
        A->>A: provision on first sight (email and/or phone claim)
        A-->>W: 200 { user, plan, usage }
    else invalid / expired
        A-->>W: 401 (client re-auths with Supabase)
    else phone-only token while AUTH_PHONE_OTP is off
        A-->>W: 401 (phone sign-in not enabled)
    end

    Note over U,A: Authenticator TOTP is NOT v0 — see roadmap.md. Phone OTP ships dark behind a flag.
```

---

## 2. Save rates / packages

```mermaid
sequenceDiagram
    actor U as Freelancer
    participant W as Next.js
    participant A as FastAPI /v1
    participant Auth as Supabase Auth
    participant DB as Postgres

    U->>W: enter 1–3 packages (label + amount), and/or hourly rate, quote currency
    W->>A: PUT /v1/me (JWT, packages[], hourly_rate?, quote_currency)
    A->>Auth: verify JWT
    A->>A: validate — amounts are integer minor units, currency in USD / INR / EUR / GBP
    Note over A: No LLM. No quota. This is the money the proposal will use.
    A->>DB: upsert Packages rows (with sort_order)
    A->>DB: UPDATE users.hourly_rate, users.quote_currency
    A-->>W: 200 updated profile
```

---

## 3. Generate — full hop list (price assembly BEFORE the model)

```mermaid
sequenceDiagram
    actor U as Freelancer
    participant W as Next.js
    participant A as FastAPI /v1
    participant Auth as Supabase Auth
    participant DB as Postgres
    participant LLM as LLM adapter

    U->>W: fill brief (<=1500) + notes (<=1000) + service_type + tone + pricing_mode, click Generate
    W->>A: POST /v1/proposals (JWT, brief_text, notes, service_type, tone, pricing_mode)

    A->>Auth: verify JWT, take sub as user_id
    A->>DB: load user + plan + current-period UsageRecord
    A->>A: quota check (proposals_count < plan.proposals_included)

    alt over quota
        Note over A: No LLM call. 0 quota.
        A-->>W: 402 + upgrade CTA
    else within quota
        A->>DB: load user's Packages + hourly_rate
        A->>A: PRICING ASSEMBLER — build authoritative pricing[].amount from user amounts (BEFORE model)
        A->>A: ingress guards — enforce char caps, strip / flag instruction-like patterns (spec §16)
        A->>DB: persist proposal row (inputs + assembled prices, proposal_json pending, pdf_url null)

        Note over A,LLM: AI inference — touchpoint 1. Structured copy only. Model has NO authority over money. No streaming.
        A->>LLM: system prompt (cached) + user payload + JSON schema + max_tokens
        LLM-->>A: JSON copy — executive_summary, scope_of_work[], timeline[], pricing[].justification, terms[], followup_email

        A->>A: egress — schema validate, drop unknown keys, STRIP / OVERWRITE any pricing[].amount with server values (spec §9, §16)
        A->>A: content check — block empty sections, credential dumps, malware links

        alt parse / validate fail (nothing valid to save)
            Note over A: Product rule: parse fail = no quota. At most 1 automatic retry, no retry storm.
            A-->>W: 502 generation failed (0 quota)
        else success
            A->>DB: save proposal_json (server-only) + llm_input_tokens / llm_output_tokens
            A->>DB: UsageRecords.proposals_count += 1
            A-->>W: 201 view DTO (preview sections + form fields — NOT raw proposal_json)
        end
    end
```

---

## 4. Edit without generate

```mermaid
sequenceDiagram
    actor U as Freelancer
    participant W as Next.js
    participant A as FastAPI /v1
    participant Auth as Supabase Auth
    participant DB as Postgres

    U->>W: edit copy (summary / scope bullet / terms) OR change a package amount, in a form
    W->>A: PATCH /v1/proposals/{id} (JWT, allowlisted fields only)
    A->>Auth: verify JWT + ownership (proposal.user_id == sub)
    A->>A: reject any key not on the PATCH allowlist

    Note over A: No LLM. No quota. Price edits are plain writes — they do NOT call the model (spec §7, §9).
    A->>DB: UPDATE the allowlisted proposal_json fields
    A->>DB: set pdf_url = NULL  (invalidate cached PDF)
    A-->>W: 200 updated view DTO
```

---

## 5. PDF — first hit vs cache hit

```mermaid
sequenceDiagram
    actor U as Freelancer
    participant W as Next.js
    participant A as FastAPI /v1
    participant Auth as Supabase Auth
    participant DB as Postgres
    participant S as Private storage

    U->>W: click Download PDF
    W->>A: GET /v1/proposals/{id}/pdf (JWT)
    A->>Auth: verify JWT + ownership
    A->>DB: load proposal (proposal_json, pdf_url, plan)

    alt cache MISS (pdf_url is null)
        Note over A: No LLM. No quota. Render from the structured record only.
        A->>A: render PDF from proposal_json, apply watermark if plan == Free
        A->>S: put object (private)
        S-->>A: storage key
        A->>DB: UPDATE proposal.pdf_url = key
        A->>S: create signed URL (short TTL)
        A-->>W: 200 { url }
    else cache HIT (pdf_url set)
        Note over A: No LLM. No quota. No re-render.
        A->>S: create signed URL (short TTL) for existing object
        A-->>W: 200 { url }
    end

    W-->>U: browser downloads from the signed URL
```

---

## 6. Subscribe — India Starter (Razorpay)

The `/billing` page loads hosted Razorpay **Checkout.js**
(`https://checkout.razorpay.com/v1/checkout.js`) via `next/script` on that route **only** (S-006). The
modal opens with the amount taken **straight from the `POST /v1/billing/checkout-session` response** —
never computed client-side. The browser "success" handler shows a pending note and does a single
`GET /v1/me` refetch; it does **not** flip the plan client-side. A missing / mock key or a
script-load failure degrades to the S-004 order-summary fallback.

```mermaid
sequenceDiagram
    actor U as Freelancer
    participant W as Next.js
    participant A as FastAPI /v1
    participant Auth as Supabase Auth
    participant Pay as Razorpay
    participant DB as Postgres

    W->>W: /billing mounts, next/script loads checkout.razorpay.com/v1/checkout.js (this route only)
    U->>W: choose Starter (India, ₹500 / 20), pay
    W->>A: POST /v1/billing/checkout-session (JWT, plan = starter_inr)
    A->>Auth: verify JWT
    A->>A: resolve SKU from in-code catalog (amount in paise)
    A->>Pay: create subscription / order
    Pay-->>A: subscription id + checkout params
    A-->>W: checkout params (provider_order_id, key_id, amount_paise, currency)

    alt real key + Checkout.js loaded
        W->>Pay: open Razorpay hosted checkout (amount = amount_paise straight from the response, never computed client-side)
        alt success handoff
            Pay-->>W: payment id + signature (client handoff, UX only)
            W->>W: show "payment received, your plan updates in a moment"
            W->>A: GET /v1/me (single refetch, no poll, no client-side plan flip)
            A-->>W: plan stays free until the webhook lands
        else modal.ondismiss
            Pay-->>W: dismissed, neutral "checkout cancelled", plan and usage unchanged
        else payment.failed
            Pay-->>W: reason, error note, button back to idle, retry without reload
        end
    else missing / mock key, or Checkout.js failed to load
        W->>W: S-004 fallback, show order id + amount, "the webhook completes the upgrade"
    end

    Note over Pay,A: authoritative state change comes from the webhook, not the browser
    Pay->>A: POST /v1/billing/webhook (event + signature)
    A->>A: verify HMAC (hmac.compare_digest)
    A->>DB: WebhookEvents upsert on unique (provider, provider_event_id)

    alt duplicate event
        Note over A: idempotent — already processed
        A-->>Pay: 200
    else new event
        A->>DB: update Subscriptions (status, current_period_end), set users.plan_id, anchor UsageRecords period
        A-->>Pay: 200
    end

    Note over U,DB: No LLM anywhere in checkout or webhook. No quota consumed.
```

---

## 7. Regenerate

Same rules as Generate: quota is checked and consumed, prices are re-assembled from the user's saved
amounts **before** the model, model output is schema-validated and price-stripped.

```mermaid
sequenceDiagram
    actor U as Freelancer
    participant W as Next.js
    participant A as FastAPI /v1
    participant Auth as Supabase Auth
    participant DB as Postgres
    participant LLM as LLM adapter

    U->>W: click Regenerate on an existing proposal
    W->>A: POST /v1/proposals/{id}/regenerate (JWT)
    A->>Auth: verify JWT + ownership
    A->>DB: load proposal inputs + plan + current-period UsageRecord
    A->>A: quota check

    alt over quota
        Note over A: No LLM. 0 quota.
        A-->>W: 402 + upgrade CTA
    else within quota
        A->>DB: reload user's Packages + hourly_rate
        A->>A: re-assemble authoritative pricing[].amount (BEFORE model)
        A->>A: ingress guards on stored brief + notes

        Note over A,LLM: AI inference — touchpoint 2. Same price-overwrite rules. No streaming.
        A->>LLM: system prompt (cached) + payload + schema + max_tokens
        LLM-->>A: JSON copy

        A->>A: egress — schema validate, drop unknown keys, overwrite pricing[].amount with server values
        alt parse / validate fail
            A-->>W: 502 (0 quota)
        else success
            A->>DB: replace proposal_json, update token counts, set pdf_url = NULL
            A->>DB: UsageRecords.proposals_count += 1
            A-->>W: 200 view DTO
        end
    end
```

---

## 8. v1.1 GHOST — competitor upload + extract (NOT v0)

> **This diagram is not v0.** It is drawn so a reviewer can see *where* the second AI hop would live
> if/when competitor compare ships (v1.1, **Pro+ only**, `mvp-spec.md` §17). No v0 endpoint, no v0
> upload surface. Optional second AI hop shown dashed.

```mermaid
sequenceDiagram
    actor U as Freelancer (Pro+)
    participant W as Next.js
    participant A as FastAPI /v1
    participant Q as Worker queue
    participant V as Vision / OCR adapter
    participant LLM as LLM adapter
    participant S as Private storage
    participant DB as Postgres

    U->>W: upload competitor quote (PDF <= 8 pages, or image <= 5 MB, client-compressed)
    W->>A: POST /v1/proposals/{id}/competitor-quote (multipart) — v1.1, Pro+ ONLY
    A->>A: guard — MIME allowlist + size cap + page cap, reject 50-page scan decks
    A->>S: store original (private)
    A->>Q: enqueue extract job
    A-->>W: 202 accepted (async)

    Q->>V: extract ONCE (vendor, currency, line items, totals)
    Note over Q,V: AI inference — v1.1 ONLY. Vision / OCR. Never in v0.
    V-->>Q: extracted_json
    Q->>DB: save CompetitorQuotes.extracted_json

    Q->>LLM: "position our packages vs this extract" — numbers only
    Note over Q,LLM: AI inference — v1.1 ONLY. Small second text call. Counts as 1 generate so Starter cannot farm vision.
    LLM-->>Q: comparison copy
    Q->>DB: save comparison block

    U->>W: reopen proposal
    W->>A: GET /v1/proposals/{id}
    A-->>W: view DTO incl. side-by-side comparison (re-compare reuses extracted_json — no new vision call)
```

---

## Sequence → AI/quota summary

| # | Journey | LLM hop? | Quota? |
|---|---|---|---|
| 1 | Sign in → JWT | No | No |
| 2 | Save rates / packages | No | No |
| 3 | Generate | **Yes — touchpoint 1** | 1 on saved success, 0 on fail |
| 4 | Edit without generate | No | No |
| 5 | PDF first hit / cache hit | No | No |
| 6 | Subscribe India Starter | No | No |
| 7 | Regenerate | **Yes — touchpoint 2** | 1 on saved success, 0 on fail |
| 8 | Competitor upload (v1.1 ghost) | Yes — **v1.1 only**, not v0 | v1.1: 1 generate |
