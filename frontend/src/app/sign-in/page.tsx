"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { createClient } from "@/lib/supabase/client";

// Auth per the AUTH OVERRIDE recorded in docs/architecture.md:
// email/password (verified) + Google. No SMS OTP, no TOTP in v0.
export default function SignInPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function signInWithEmail(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const { error } = await createClient().auth.signInWithPassword({ email, password });
    setBusy(false);
    if (error) {
      setError(error.message);
      return;
    }
    router.push("/");
  }

  async function signInWithGoogle() {
    await createClient().auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: `${window.location.origin}/` },
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
