"use client";

import { useEffect, useState } from "react";

import { toMinor } from "@/lib/format";
import type { ProposalStatus, ProposalView } from "@/lib/types";

const STATUSES: ProposalStatus[] = ["draft", "sent", "won", "lost"];

/**
 * The right-rail editor. Every field maps to an allowlisted PATCH path — there
 * is no JSON view. Editing a PRICE field sends a normal PATCH (`onPatch`); it
 * never triggers a regenerate (mvp-spec.md §7, §9).
 */
export function SectionForms({
  proposal,
  onPatch,
}: {
  proposal: ProposalView;
  onPatch: (body: Record<string, unknown>) => Promise<void>;
}) {
  const s = proposal.sections;
  const [summary, setSummary] = useState(s?.executive_summary ?? "");
  const [scope, setScope] = useState((s?.scope_of_work ?? []).join("\n"));
  const [terms, setTerms] = useState((s?.terms ?? []).join("\n"));
  const [followup, setFollowup] = useState(s?.followup_email ?? "");
  const [prices, setPrices] = useState(
    proposal.pricing.map((l) => ({ label: l.label, amount: String(l.amount_minor / 100) })),
  );
  const [priceError, setPriceError] = useState<string | null>(null);

  useEffect(() => {
    setSummary(s?.executive_summary ?? "");
    setScope((s?.scope_of_work ?? []).join("\n"));
    setTerms((s?.terms ?? []).join("\n"));
    setFollowup(s?.followup_email ?? "");
    setPrices(
      proposal.pricing.map((l) => ({ label: l.label, amount: String(l.amount_minor / 100) })),
    );
  }, [proposal, s]);

  function commitSections() {
    onPatch({
      sections: {
        executive_summary: summary,
        scope_of_work: scope.split("\n").map((x) => x.trim()).filter(Boolean),
        terms: terms.split("\n").map((x) => x.trim()).filter(Boolean),
        followup_email: followup,
      },
    });
  }

  function commitPrices() {
    setPriceError(null);
    const pricing = [];
    for (const p of prices) {
      const amt = toMinor(p.amount);
      if (amt === null) {
        setPriceError("Prices must be non-negative numbers.");
        return;
      }
      pricing.push({ label: p.label, amount_minor: amt });
    }
    // A plain PATCH — NOT a regenerate.
    onPatch({ pricing });
  }

  return (
    <div className="space-y-5 text-sm">
      <label className="block">
        <span className="font-medium">Status</span>
        <select
          value={proposal.status}
          onChange={(e) => onPatch({ status: e.target.value })}
          className="mt-1 w-full rounded border px-2 py-1"
        >
          {STATUSES.map((st) => (
            <option key={st}>{st}</option>
          ))}
        </select>
      </label>

      <label className="block">
        <span className="font-medium">Client name</span>
        <input
          value={proposal.client_name}
          onChange={(e) => onPatch({ client_name: e.target.value })}
          className="mt-1 w-full rounded border px-2 py-1"
        />
      </label>

      <label className="block">
        <span className="font-medium">Executive summary</span>
        <textarea
          value={summary}
          onChange={(e) => setSummary(e.target.value)}
          onBlur={commitSections}
          className="mt-1 h-24 w-full rounded border px-2 py-1"
        />
      </label>

      <label className="block">
        <span className="font-medium">Scope (one per line)</span>
        <textarea
          value={scope}
          onChange={(e) => setScope(e.target.value)}
          onBlur={commitSections}
          className="mt-1 h-24 w-full rounded border px-2 py-1"
        />
      </label>

      <label className="block">
        <span className="font-medium">Terms (one per line)</span>
        <textarea
          value={terms}
          onChange={(e) => setTerms(e.target.value)}
          onBlur={commitSections}
          className="mt-1 h-20 w-full rounded border px-2 py-1"
        />
      </label>

      <label className="block">
        <span className="font-medium">Follow-up email</span>
        <textarea
          value={followup}
          onChange={(e) => setFollowup(e.target.value)}
          onBlur={commitSections}
          className="mt-1 h-24 w-full rounded border px-2 py-1"
        />
      </label>

      <div>
        <span className="font-medium">Prices (your numbers — editing here does not re-run the AI)</span>
        <div className="mt-1 space-y-2">
          {prices.map((p, i) => (
            <div key={i} className="flex gap-2">
              <input
                aria-label={`price label ${i}`}
                value={p.label}
                onChange={(e) =>
                  setPrices(prices.map((x, j) => (j === i ? { ...x, label: e.target.value } : x)))
                }
                onBlur={commitPrices}
                className="flex-1 rounded border px-2 py-1"
              />
              <input
                aria-label={`price amount ${i}`}
                inputMode="decimal"
                value={p.amount}
                onChange={(e) =>
                  setPrices(prices.map((x, j) => (j === i ? { ...x, amount: e.target.value } : x)))
                }
                onBlur={commitPrices}
                className="w-28 rounded border px-2 py-1"
              />
            </div>
          ))}
        </div>
        {priceError && <p className="mt-1 text-red-600">{priceError}</p>}
      </div>
    </div>
  );
}
