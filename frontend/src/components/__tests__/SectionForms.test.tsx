import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { SectionForms } from "@/components/SectionForms";
import type { ProposalView } from "@/lib/types";

const proposal: ProposalView = {
  id: "p1",
  client_name: "Acme Co",
  client_company: null,
  service_type: "web_dev",
  tone: "formal",
  pricing_mode: "fixed",
  status: "draft",
  language: "en",
  pdf_url: null,
  created_at: "2026-08-29T00:00:00Z",
  updated_at: "2026-08-29T00:00:00Z",
  sections: {
    executive_summary: "Summary",
    scope_of_work: ["Item"],
    timeline: [],
    terms: ["Term"],
    followup_email: "Hi",
  },
  pricing: [{ label: "Project", amount_minor: 500000, currency: "INR", justification: "" }],
};

it("editing a price sends a plain PATCH (pricing), never a regenerate", async () => {
  const onPatch = jest.fn().mockResolvedValue(undefined);
  render(<SectionForms proposal={proposal} onPatch={onPatch} />);

  const amount = screen.getByLabelText("price amount 0");
  await userEvent.clear(amount);
  await userEvent.type(amount, "7500");
  await userEvent.tab(); // blur -> commit

  expect(onPatch).toHaveBeenCalledWith({
    pricing: [{ label: "Project", amount_minor: 750000 }],
  });
  // The body is a PATCH allowlist payload — it carries no "regenerate" intent
  // and no raw json.
  const body = onPatch.mock.calls[0][0];
  expect(JSON.stringify(body)).not.toMatch(/regenerate|proposal_json/);
});

it("editing a section field PATCHes sections.*", async () => {
  const onPatch = jest.fn().mockResolvedValue(undefined);
  render(<SectionForms proposal={proposal} onPatch={onPatch} />);

  const summary = screen.getByDisplayValue("Summary");
  await userEvent.type(summary, " edited");
  await userEvent.tab();

  const call = onPatch.mock.calls.at(-1)![0];
  expect(call).toHaveProperty("sections.executive_summary", "Summary edited");
});
