"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

import { createClient } from "@/lib/supabase/client";

export function Nav() {
  const router = useRouter();

  async function signOut() {
    await createClient().auth.signOut();
    router.push("/sign-in");
  }
  // createClient() is called lazily inside the handler so a build-time prerender
  // (no env) never constructs the Supabase client.

  return (
    <header className="border-b bg-white">
      <nav className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
        <Link href="/" className="font-semibold">
          AIProposer
        </Link>
        <div className="flex items-center gap-4 text-sm">
          <Link href="/" className="hover:underline">
            Proposals
          </Link>
          <Link href="/settings" className="hover:underline">
            Settings
          </Link>
          <button onClick={signOut} className="text-neutral-500 hover:text-ink">
            Sign out
          </button>
        </div>
      </nav>
    </header>
  );
}
