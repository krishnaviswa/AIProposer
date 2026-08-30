import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";
import { NextResponse, type NextRequest } from "next/server";

/**
 * The single auth-redirect landing (ADR-004). Every sign-in path funnels here:
 * Google OAuth (`redirectTo`), Supabase email-verification / magic links, and
 * the email/password page's hard navigation after `signInWithPassword`.
 *
 * This route handler does exactly two things and nothing else:
 *   1. a Supabase Auth **session** operation — `exchangeCodeForSession(code)`
 *      when a PKCE `?code=` is present (the same category as `signInWithPassword`);
 *   2. an HTTP redirect.
 * No `/v1` call, no pricing / quota / proposal logic — the route stays on the
 * right side of CLAUDE.md non-negotiable #5 and frontend/CLAUDE.md's boundary.
 * FastAPI remains the only JWT verifier and the only holder of business logic.
 *
 * v0 redirect targets are fixed — no `next` / `redirectTo` param is read
 * (see ADR-004; a same-origin-guarded variant is a roadmap item):
 *   - `?error=` / `?error_description=`, or the exchange throws -> `/sign-in?error=…`, no session
 *   - `?code=` exchanged OK                                     -> `/`  + Set-Cookie session
 *   - no `?code=` but a valid session already on the request    -> `/`   (the email/password path)
 *   - no `?code=` and no session                                -> `/sign-in`
 */
export async function GET(request: NextRequest) {
  const { searchParams, origin } = request.nextUrl;
  const code = searchParams.get("code");
  const errorParam = searchParams.get("error_description") ?? searchParams.get("error");

  const toSignIn = (msg?: string) =>
    NextResponse.redirect(
      new URL(msg ? `/sign-in?error=${encodeURIComponent(msg)}` : "/sign-in", origin),
    );

  if (errorParam) return toSignIn(errorParam);

  const cookieStore = await cookies();
  let response = NextResponse.redirect(new URL("/", origin));
  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll: () => cookieStore.getAll(),
        setAll: (cookiesToSet) => {
          cookiesToSet.forEach(({ name, value, options }) =>
            response.cookies.set(name, value, options),
          );
        },
      },
    },
  );

  if (code) {
    const { error } = await supabase.auth.exchangeCodeForSession(code);
    if (error) return toSignIn(error.message);
    return response;
  }

  // No code — only let the request through if a session already exists
  // (the email/password page hard-navigates here with the cookie already set).
  const {
    data: { user },
  } = await supabase.auth.getUser();
  return user ? response : toSignIn();
}
