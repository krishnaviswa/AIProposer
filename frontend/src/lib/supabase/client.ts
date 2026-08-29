import { createBrowserClient } from "@supabase/ssr";

/**
 * Supabase browser client — used ONLY for the auth session (sign in, get the
 * access token). Every data operation goes through FastAPI (`src/lib/api.ts`).
 */
export function createClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
  );
}
