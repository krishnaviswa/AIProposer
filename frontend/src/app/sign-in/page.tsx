"use client";

import { useEffect, useState } from "react";

import { createClient } from "@/lib/supabase/client";

// Auth per the AUTH OVERRIDE recorded in docs/architecture.md:
// email/password (verified) + Google. No SMS OTP, no TOTP in v0.
//
// Every sign-in path lands on /auth/callback (ADR-004): Google via `redirectTo`,
// email/password via a hard navigation so the route handler actually runs. The
// callback exchanges the code / confirms the session, then redirects to `/`.
export default function SignInPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

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

  return (
    <main className="mx-auto flex min-h-screen max-w-sm flex-col justify-center px-4">
      <h1 className="mb-1 text-2xl font-semibold">Sign in to AIProposer</h1>
      <p className="mb-6 text-sm text-neutral-500">
        Verified email or Google. No SMS in v0.
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
    </main>
  );
}
