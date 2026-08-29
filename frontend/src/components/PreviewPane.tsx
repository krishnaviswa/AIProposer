import { money } from "@/lib/format";
import { FREE_PLAN_ID, type ProposalView } from "@/lib/types";
import { WatermarkBanner } from "@/components/WatermarkBanner";

/**
 * The PDF-like preview. Read-only render of the view DTO — there is deliberately
 * no way to see or copy the raw `proposal_json` (mvp-spec.md §15.2). On Free the
 * preview carries a watermark.
 */
export function PreviewPane({ proposal, planId }: { proposal: ProposalView; planId: string }) {
  const s = proposal.sections;
  const isFree = planId === FREE_PLAN_ID;

  return (
    <article
      data-testid="preview-pane"
      className={
        "prose-preview relative rounded border bg-white p-8 " +
        (isFree ? "select-none" : "")
      }
    >
      <WatermarkBanner planId={planId} />
      {isFree && (
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 flex items-center justify-center overflow-hidden"
        >
          <span className="rotate-[-30deg] text-6xl font-black text-neutral-200">
            NOT FOR SENDING
          </span>
        </div>
      )}

      <header className="mb-6">
        <h1 className="text-2xl font-bold">Proposal for {proposal.client_name}</h1>
        {proposal.client_company && (
          <p className="text-neutral-500">{proposal.client_company}</p>
        )}
      </header>

      {!s && <p className="text-neutral-500">Not generated yet.</p>}

      {s && (
        <>
          <h2>Executive summary</h2>
          <p>{s.executive_summary}</p>

          <h2>Scope of work</h2>
          <ul>
            {s.scope_of_work.map((item, i) => (
              <li key={i}>{item}</li>
            ))}
          </ul>

          <h2>Timeline</h2>
          <ul>
            {s.timeline.map((t, i) => (
              <li key={i}>
                <strong>{t.label}:</strong> {t.detail}
              </li>
            ))}
          </ul>

          <h2>Pricing</h2>
          <ul>
            {proposal.pricing.map((line, i) => (
              <li key={i}>
                <strong>{line.label}:</strong> {money(line.amount_minor, line.currency)}
                {line.justification && (
                  <span className="block text-sm text-neutral-500">{line.justification}</span>
                )}
              </li>
            ))}
          </ul>

          <h2>Terms</h2>
          <ul>
            {s.terms.map((t, i) => (
              <li key={i}>{t}</li>
            ))}
          </ul>

          {!isFree && (
            <>
              <h2>Follow-up email</h2>
              <p className="whitespace-pre-wrap text-sm text-neutral-600">{s.followup_email}</p>
            </>
          )}
        </>
      )}
    </article>
  );
}
