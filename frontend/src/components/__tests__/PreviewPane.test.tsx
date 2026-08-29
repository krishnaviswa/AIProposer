import { render, screen } from "@testing-library/react";

import { PreviewPane } from "@/components/PreviewPane";
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
    executive_summary: "A short summary.",
    scope_of_work: ["Do the thing"],
    timeline: [{ label: "Week 1", detail: "Kickoff" }],
    terms: ["50% upfront"],
    followup_email: "Hi there",
  },
  pricing: [{ label: "Project", amount_minor: 500000, currency: "INR", justification: "" }],
};

it("renders the proposal without exposing any JSON / export affordance", () => {
  render(<PreviewPane proposal={proposal} planId="starter_inr" />);
  expect(screen.getByText("Proposal for Acme Co")).toBeInTheDocument();
  expect(screen.getByText("₹5,000")).toBeInTheDocument();

  // The whole point of §15.2: no raw source, no export.
  expect(screen.queryByText(/export json/i)).not.toBeInTheDocument();
  expect(screen.queryByText(/copy source/i)).not.toBeInTheDocument();
  expect(screen.queryByText(/proposal_json/i)).not.toBeInTheDocument();
});

it("shows the NOT-FOR-SENDING watermark and hides the follow-up email on Free", () => {
  render(<PreviewPane proposal={proposal} planId="free" />);
  expect(screen.getByTestId("free-watermark")).toBeInTheDocument();
  expect(screen.getByText("NOT FOR SENDING")).toBeInTheDocument();
  expect(screen.queryByText("Follow-up email")).not.toBeInTheDocument();
});

it("has no watermark on a paid plan", () => {
  render(<PreviewPane proposal={proposal} planId="starter_inr" />);
  expect(screen.queryByTestId("free-watermark")).not.toBeInTheDocument();
  expect(screen.getByText("Follow-up email")).toBeInTheDocument();
});
