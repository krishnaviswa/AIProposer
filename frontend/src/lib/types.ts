// Mirrors the FastAPI view DTOs (backend/app/schemas). The raw `proposal_json`
// is never sent to the client, so there is no type for it here.

export type Currency = "USD" | "INR" | "EUR" | "GBP";
export type ServiceType =
  | "web_dev"
  | "design"
  | "video"
  | "marketing"
  | "consulting"
  | "other";
export type Tone = "formal" | "friendly" | "persuasive";
export type PricingMode = "packages" | "hourly" | "fixed";
export type ProposalStatus = "draft" | "sent" | "won" | "lost";

export interface PackageOut {
  id: string;
  label: string;
  amount_minor: number;
  currency: string;
}

export interface MeView {
  id: string;
  email: string;
  name: string | null;
  quote_currency: string;
  hourly_rate_minor: number | null;
  plan: { id: string; name: string; proposals_included: number };
  packages: PackageOut[];
  usage: { included: number; used: number; remaining: number; period_end: string };
}

export interface PricingLine {
  label: string;
  amount_minor: number;
  currency: string;
  justification: string;
}

export interface ProposalSections {
  executive_summary: string;
  scope_of_work: string[];
  timeline: { label: string; detail: string }[];
  terms: string[];
  followup_email: string;
}

export interface ProposalView {
  id: string;
  client_name: string;
  client_company: string | null;
  service_type: string;
  tone: string;
  pricing_mode: string;
  status: ProposalStatus;
  language: string;
  pdf_url: string | null;
  created_at: string;
  updated_at: string;
  sections: ProposalSections | null;
  pricing: PricingLine[];
}

export const FREE_PLAN_ID = "free";
