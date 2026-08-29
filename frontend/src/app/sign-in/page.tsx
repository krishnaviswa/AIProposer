"use client";

import { useEffect, useState } from "react";

import { createClient } from "@/lib/supabase/client";

// Auth per the AUTH OVERRIDE in docs/architecture.md: verified email + Google,
// plus phone OTP as an OPTIONAL method behind NEXT_PUBLIC_AUTH_PHONE_OTP
// (ADR-003). The flag is off by default; when off, only email + Google render.
//
// Every sign-in path lands on /auth/callback (ADR-004): Google via `redirectTo`,
// email/password and phone OTP via a hard navigation so the route handler runs.
// The callback exchanges the code / confirms the session, then redirects to `/`.
export default function SignInPage() {
  const PHONE_OTP_ENABLED = process.env.NEXT_PUBLIC_AUTH_PHONE_OTP === "true";
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // Phone OTP: request a code, then verify it.
  const [phone, setPhone] = useState("");
  const [code, setCode] = useState("");
  const [codeSent, setCodeSent] = useState(false);

  // /auth/callback bounces failures back here as ?error=…
  useEffect(() => {
    const msg = new URLSearchParams(window.location.search).get("error");
    if (msg) setError(msg);
  }, []);

  async function signInWithEmail(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const { error } = await createClient().auth.signInWithPassword({ email, password });
    if (error) {
      setBusy(false);
      setError(error.message);
      return;
    }
    // Hard nav (not router.push) so the /auth/callback route handler runs with
    // the freshly-set session cookie.
    window.location.assign("/auth/callback");
  }

  async function signInWithGoogle() {
    await createClient().auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: `${window.location.origin}/auth/callback` },
    });
  }

  async function sendPhoneCode(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const { error } = await createClient().auth.signInWithOtp({ phone });
    setBusy(false);
    if (error) {
      setError(error.message);
      return;
    }
    setCodeSent(true);
  }

  async function verifyPhoneCode(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const { error } = await createClient().auth.verifyOtp({ phone, token: code, type: "sms" });
    if (error) {
      setBusy(false);
      setError(error.message);
      return;
    }
    // Same hard nav as the other paths — land on /auth/callback so the session
    // is confirmed there before redirecting to `/` (ADR-004).
    window.location.assign("/auth/callback");
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-sm flex-col justify-center px-4">
      <h1 className="mb-1 text-2xl font-semibold">Sign in to AIProposer</h1>
      <p className="mb-6 text-sm text-neutral-500">
        {PHONE_OTP_ENABLED ? "Verified email, Google, or phone." : "Verified email or Google."}
      </p>

      <form onSubmit={signInWithEmail} className="space-y-3">
        <input
          type="email"
          required
          placeholder="you@example.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="w-full rounded border px-3 py-2"
        />
        <input
          type="password"
          required
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="w-full rounded border px-3 py-2"
        />
        {error && <p className="text-sm text-red-600">{error}</p>}
        <button
          type="submit"
          disabled={busy}
          className="w-full rounded bg-accent px-3 py-2 text-white disabled:opacity-50"
        >
          {busy ? "Signing in…" : "Continue"}
        </button>
      </form>

      <button
        onClick={signInWithGoogle}
        className="mt-3 w-full rounded border px-3 py-2 text-sm hover:bg-neutral-50"
      >
        Continue with Google
      </button>

      {PHONE_OTP_ENABLED && (
        <div className="mt-6 border-t pt-4">
          <p className="mb-2 text-sm font-medium">Or sign in with your phone</p>
          {!codeSent ? (
            <form onSubmit={sendPhoneCode} className="space-y-3">
              <input
                type="tel"
                required
                placeholder="+91 90000 00000"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                className="w-full rounded border px-3 py-2"
              />
              <button
                type="submit"
                disabled={busy}
                className="w-full rounded border px-3 py-2 text-sm hover:bg-neutral-50 disabled:opacity-50"
              >
                {busy ? "Sending…" : "Send code"}
              </button>
            </form>
          ) : (
            <form onSubmit={verifyPhoneCode} className="space-y-3">
              <input
                type="text"
                inputMode="numeric"
                required
                placeholder="6-digit code"
                value={code}
                onChange={(e) => setCode(e.target.value)}
                className="w-full rounded border px-3 py-2"
              />
              <button
                type="submit"
                disabled={busy}
                className="w-full rounded bg-accent px-3 py-2 text-sm text-white disabled:opacity-50"
              >
                {busy ? "Verifying…" : "Verify & continue"}
              </button>
              <button
                type="button"
                onClick={() => setCodeSent(false)}
                className="w-full text-xs text-neutral-500 underline"
              >
                Use a different number
              </button>
            </form>
          )}
        </div>
      )}
    </main>
  );
}
