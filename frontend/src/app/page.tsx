"use client";

import Link from "next/link";

import { Nav } from "@/components/Nav";
import { api } from "@/lib/api";
import { money } from "@/lib/format";
import { useResource } from "@/lib/useApi";
import type { MeView, ProposalView } from "@/lib/types";

export default function DashboardPage() {
  const me = useResource<MeView>(() => api.getMe());
  const proposals = useResource<ProposalView[]>(() => api.listProposals());

  return (
    <>
      <Nav />
      <main className="mx-auto max-w-5xl px-4 py-8">
        <div className="mb-6 flex items-end justify-between">
          <div>
            <h1 className="text-2xl font-semibold">Proposals</h1>
            {me.data && (
              <p className="text-sm text-neutral-500">
                {me.data.plan.name} · {me.data.usage.used}/{me.data.usage.included} used this period ·{" "}
                <Link href="/billing" className="text-accent underline">
                  Plan &amp; billing
                </Link>
              </p>
            )}
          </div>
          <Link
            href="/proposals/new"
            className="rounded bg-accent px-4 py-2 text-sm text-white"
          >
            New proposal
          </Link>
        </div>

        {proposals.loading && <p className="text-neutral-500">Loading…</p>}
        {proposals.error && <p className="text-red-600">Could not load proposals.</p>}

        {proposals.data?.length === 0 && (
          <div className="rounded border border-dashed p-10 text-center text-neutral-500">
            No proposals yet. <Link href="/proposals/new" className="text-accent underline">Create one</Link>.
          </div>
        )}

        <ul className="divide-y rounded border bg-white">
          {proposals.data?.map((p) => (
            <li key={p.id}>
              <Link
                href={`/proposals/${p.id}`}
                className="flex items-center justify-between px-4 py-3 hover:bg-neutral-50"
              >
                <span>
                  <span className="font-medium">{p.client_name}</span>
                  <span className="ml-2 text-xs uppercase text-neutral-400">{p.status}</span>
                </span>
                <span className="text-sm text-neutral-500">
                  {p.pricing.map((l) => money(l.amount_minor, l.currency)).join(" · ") || "—"}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      </main>
    </>
  );
}
