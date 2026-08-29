/**
 * @jest-environment node
 */
import type { NextRequest } from "next/server";

import { GET } from "@/app/auth/callback/route";

const exchangeCodeForSession = jest.fn();
const getUser = jest.fn();

jest.mock("next/headers", () => ({
  cookies: async () => ({ getAll: () => [], set: () => {} }),
}));
jest.mock("@supabase/ssr", () => ({
  createServerClient: () => ({ auth: { exchangeCodeForSession, getUser } }),
}));

const req = (url: string) =>
  ({ nextUrl: new URL(url, "http://localhost:3000") }) as unknown as NextRequest;

beforeEach(() => {
  exchangeCodeForSession.mockReset();
  getUser.mockReset();
});

describe("/auth/callback", () => {
  it("redirects to / after a successful code exchange (AC 9)", async () => {
    exchangeCodeForSession.mockResolvedValue({ error: null });
    const res = await GET(req("/auth/callback?code=good"));
    expect(exchangeCodeForSession).toHaveBeenCalledWith("good");
    expect(res.headers.get("location")).toBe("http://localhost:3000/");
  });

  it("redirects to /sign-in with the message when the exchange fails (AC 10)", async () => {
    exchangeCodeForSession.mockResolvedValue({ error: { message: "bad code" } });
    const res = await GET(req("/auth/callback?code=bad"));
    expect(res.headers.get("location")).toBe("http://localhost:3000/sign-in?error=bad%20code");
  });

  it("redirects to /sign-in on an ?error param without touching Supabase (AC 10)", async () => {
    const res = await GET(req("/auth/callback?error=access_denied"));
    expect(exchangeCodeForSession).not.toHaveBeenCalled();
    expect(res.headers.get("location")).toBe("http://localhost:3000/sign-in?error=access_denied");
  });

  it("redirects to /sign-in when there is no code and no session (AC 11)", async () => {
    getUser.mockResolvedValue({ data: { user: null } });
    const res = await GET(req("/auth/callback"));
    expect(res.headers.get("location")).toBe("http://localhost:3000/sign-in");
  });

  it("redirects to / when there is no code but a session already exists (email/password path)", async () => {
    getUser.mockResolvedValue({ data: { user: { id: "u1" } } });
    const res = await GET(req("/auth/callback"));
    expect(res.headers.get("location")).toBe("http://localhost:3000/");
  });

  it("makes no /v1 call (AC 13) — the handler is pure Supabase-Auth + redirect", () => {
    // Fails loudly if someone wires FastAPI / business logic into the route handler.
    const fs = jest.requireActual("fs") as typeof import("fs");
    const path = jest.requireActual("path") as typeof import("path");
    const src = fs.readFileSync(path.join(__dirname, "../callback/route.ts"), "utf8");
    expect(src).not.toMatch(/lib\/api|apiFetch|\/v1\//);
  });
});
