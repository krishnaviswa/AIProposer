import { FREE_PLAN_ID } from "@/lib/types";

/**
 * Free-plan output is deliberately incomplete (mvp-spec.md §15): a watermark on
 * the preview + PDF and no follow-up-email copy button. Paid plans render clean.
 */
export function WatermarkBanner({ planId }: { planId: string }) {
  if (planId !== FREE_PLAN_ID) return null;
  return (
    <div
      data-testid="free-watermark"
      className="mb-4 rounded border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-800"
    >
      Free preview — <strong>not for sending</strong>. Upgrade to remove the watermark and export a
      clean PDF.
    </div>
  );
}
