"use client";

import { useParams, useRouter } from "next/navigation";
import { useState } from "react";

import { Nav } from "@/components/Nav";
import { PreviewPane } from "@/components/PreviewPane";
import { SectionForms } from "@/components/SectionForms";
import Link from "next/link";

import { api, ApiError, apiOrigin } from "@/lib/api";
import { useResource } from "@/lib/useApi";
import type { MeView, ProposalView } from "@/lib/types";

export default function ProposalEditorPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const me = useResource<MeView>(() => api.getMe());
  const proposal = useResource<ProposalView>(() => api.getProposal(id), [id]);
  const [banner, setBanner] = useState<string | null>(null);
  const [overQuota, setOverQuota] = useState(false);

  async function patch(body: Record<string, unknown>) {
    try {
      const updated = await api.patchProposal(id, body);
      proposal.setData(updated);
    } catch (err) {
      setBanner((err as ApiError).message);
    }
  }

  async function regenerate() {
    setBanner(null);
    setOverQuota(false);
    try {
      const updated = await api.regenerate(id);
      proposal.setData(updated);
      me.refetch();
    } catch (err) {
      const e = err as ApiError;
      if (e.status === 402) {
        setOverQuota(true);
        setBanner("You've hit your plan limit for this period.");
      } else {
        setBanner(e.message);
      }
    }
  }

  async function duplicate() {
    const copy = await api.duplicate(id);
    router.push(`/proposals/${copy.id}`);
  }

  async function downloadPdf() {
    setBanner(null);
    try {
      const { pdf_url } = await api.getPdf(id);
      const href = pdf_url.startsWith("http") ? pdf_url : `${apiOrigin()}${pdf_url}`;
      window.open(href, "_blank", "noopener");
    } catch (err) {
      setBanner((err as ApiError).message);
    }
  }

  if (proposal.loading) return <Loading />;
  if (proposal.error || !proposal.data)
    return <Loading text="Could not load this proposal." />;

  const p = proposal.data;
  const planId = me.data?.plan.id ?? "free";

  return (
    <>
      <Nav />
      <main className="mx-auto max-w-6xl px-4 py-6">
        <div className="mb-4 flex items-center justify-between">
          <h1 className="text-xl font-semibold">{p.client_name}</h1>
          <div className="flex gap-2 text-sm">
            <button onClick={regenerate} className="rounded border px-3 py-1.5">
              Regenerate
            </button>
            <button onClick={duplicate} className="rounded border px-3 py-1.5">
              Duplicate
            </button>
            <button onClick={downloadPdf} className="rounded border px-3 py-1.5">
              Download PDF
            </button>
          </div>
        </div>

        {banner && (
          <p className="mb-4 rounded bg-neutral-100 px-3 py-2 text-sm text-neutral-700">
            {banner}
            {overQuota && (
              <>
                {" "}
                <Link href="/billing" className="font-medium text-accent underline">
                  Upgrade
                </Link>
              </>
            )}
          </p>
        )}

        <div className="grid gap-6 lg:grid-cols-[1fr_360px]">
          <PreviewPane proposal={p} planId={planId} />
          <aside className="rounded border bg-white p-4">
            <SectionForms proposal={p} onPatch={patch} />
          </aside>
        </div>
      </main>
    </>
  );
}

function Loading({ text = "Loading…" }: { text?: string }) {
  return (
    <>
      <Nav />
      <main className="mx-auto max-w-6xl px-4 py-16 text-center text-neutral-500">{text}</main>
    </>
  );
}
