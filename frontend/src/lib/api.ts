import { createClient } from "@/lib/supabase/client";
import type { MeView, ProposalView } from "@/lib/types";

const BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/v1";

export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: unknown,
  ) {
    super(typeof detail === "string" ? detail : `API error ${status}`);
  }
}

/**
 * The single entry point for talking to FastAPI. Attaches the Supabase access
 * token as a bearer. Never call any other host from the web client.
 *
 * `getToken` is injectable so tests don't need a real Supabase session.
 */
export async function apiFetch<T = unknown>(
  path: string,
  init: RequestInit = {},
  getToken: () => Promise<string | null> = defaultGetToken,
): Promise<T> {
  const token = await getToken();
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const res = await fetch(`${BASE}${path}`, { ...init, headers });
  const body = res.status === 204 ? null : await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(res.status, (body as { detail?: unknown })?.detail ?? body);
  return body as T;
}

async function defaultGetToken(): Promise<string | null> {
  const supabase = createClient();
  const { data } = await supabase.auth.getSession();
  return data.session?.access_token ?? null;
}

// --- typed helpers ---------------------------------------------------------

export const api = {
  getMe: () => apiFetch<MeView>("/me"),
  putMe: (body: {
    name?: string | null;
    quote_currency: string;
    hourly_rate_minor?: number | null;
    packages: { label: string; amount_minor: number }[];
  }) => apiFetch<MeView>("/me", { method: "PUT", body: JSON.stringify(body) }),

  listProposals: () => apiFetch<ProposalView[]>("/proposals"),
  getProposal: (id: string) => apiFetch<ProposalView>(`/proposals/${id}`),
  createProposal: (body: unknown) =>
    apiFetch<ProposalView>("/proposals", { method: "POST", body: JSON.stringify(body) }),
  patchProposal: (id: string, body: unknown) =>
    apiFetch<ProposalView>(`/proposals/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  regenerate: (id: string) =>
    apiFetch<ProposalView>(`/proposals/${id}/regenerate`, { method: "POST" }),
  duplicate: (id: string) =>
    apiFetch<ProposalView>(`/proposals/${id}/duplicate`, { method: "POST" }),
  getPdf: (id: string) => apiFetch<{ pdf_url: string }>(`/proposals/${id}/pdf`),
  checkout: (plan_id: string) =>
    apiFetch<{
      provider_order_id: string;
      key_id: string;
      amount_paise: number;
      currency: string;
      plan_id: string;
    }>("/billing/checkout-session", { method: "POST", body: JSON.stringify({ plan_id }) }),
};

/** The API base without the trailing `/v1`, for resolving relative asset URLs (PDFs). */
export function apiOrigin(): string {
  return BASE.replace(/\/v1\/?$/, "");
}

export { BASE as API_BASE_URL };
