"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Nav } from "@/components/Nav";
import { api, ApiError } from "@/lib/api";
import { toMinor } from "@/lib/format";
import { useResource } from "@/lib/useApi";
import type { MeView, PricingMode, ServiceType, Tone } from "@/lib/types";

const SERVICES: ServiceType[] = ["web_dev", "design", "video", "marketing", "consulting", "other"];
const TONES: Tone[] = ["formal", "friendly", "persuasive"];

export default function NewProposalPage() {
  const router = useRouter();
  const me = useResource<MeView>(() => api.getMe());

  const [clientName, setClientName] = useState("");
  const [company, setCompany] = useState("");
  const [service, setService] = useState<ServiceType>("web_dev");
  const [tone, setTone] = useState<Tone>("formal");
  const [brief, setBrief] = useState("");
  const [notes, setNotes] = useState("");
  const [mode, setMode] = useState<PricingMode>("packages");
  const [pickedPackages, setPickedPackages] = useState<string[]>([]);
  const [hourlyRows, setHourlyRows] = useState([{ label: "Standard", hours: "10" }]);
  const [fixedLabel, setFixedLabel] = useState("Project fee");
  const [fixedAmount, setFixedAmount] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    const payload: Record<string, unknown> = {
      client_name: clientName,
      client_company: company || null,
      service_type: service,
      brief_text: brief,
      notes: notes || null,
      tone,
      pricing_mode: mode,
    };
    if (mode === "packages") payload.package_ids = pickedPackages;
    if (mode === "hourly")
      payload.hourly = hourlyRows.map((r) => ({ label: r.label, hours: Number(r.hours) }));
    if (mode === "fixed")
      payload.fixed = { label: fixedLabel, amount_minor: toMinor(fixedAmount) ?? 0 };

    setBusy(true);
    try {
      const created = await api.createProposal(payload);
      router.push(`/proposals/${created.id}`);
    } catch (err) {
      const e = err as ApiError;
      if (e.status === 402) setError("You've hit your plan limit for this period.");
      else setError(e.message);
      setBusy(false);
    }
  }

  return (
    <>
      <Nav />
      <main className="mx-auto max-w-2xl px-4 py-8">
        <h1 className="mb-6 text-2xl font-semibold">New proposal</h1>
        <form onSubmit={submit} className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <input
              required
              placeholder="Client name"
              value={clientName}
              onChange={(e) => setClientName(e.target.value)}
              className="rounded border px-3 py-2"
            />
            <input
              placeholder="Company (optional)"
              value={company}
              onChange={(e) => setCompany(e.target.value)}
              className="rounded border px-3 py-2"
            />
            <select
              value={service}
              onChange={(e) => setService(e.target.value as ServiceType)}
              className="rounded border px-3 py-2"
            >
              {SERVICES.map((s) => (
                <option key={s} value={s}>
                  {s.replace("_", " ")}
                </option>
              ))}
            </select>
            <select
              value={tone}
              onChange={(e) => setTone(e.target.value as Tone)}
              className="rounded border px-3 py-2"
            >
              {TONES.map((t) => (
                <option key={t}>{t}</option>
              ))}
            </select>
          </div>

          <textarea
            required
            maxLength={1500}
            placeholder="Paste the client brief (max 1500 chars)"
            value={brief}
            onChange={(e) => setBrief(e.target.value)}
            className="h-32 w-full rounded border px-3 py-2"
          />
          <textarea
            maxLength={1000}
            placeholder="Notes (optional, max 1000 chars)"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            className="h-20 w-full rounded border px-3 py-2"
          />

          <fieldset className="rounded border p-3">
            <legend className="px-1 text-sm">Pricing</legend>
            <div className="mb-3 flex gap-3 text-sm">
              {(["packages", "hourly", "fixed"] as PricingMode[]).map((m) => (
                <label key={m} className="flex items-center gap-1">
                  <input
                    type="radio"
                    checked={mode === m}
                    onChange={() => setMode(m)}
                  />
                  {m}
                </label>
              ))}
            </div>

            {mode === "packages" && (
              <div className="space-y-1 text-sm">
                {me.data?.packages.length === 0 && (
                  <p className="text-neutral-500">
                    No saved packages — add some in Settings, or use hourly / fixed.
                  </p>
                )}
                {me.data?.packages.map((p) => (
                  <label key={p.id} className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={pickedPackages.includes(p.id)}
                      onChange={(e) =>
                        setPickedPackages(
                          e.target.checked
                            ? [...pickedPackages, p.id]
                            : pickedPackages.filter((x) => x !== p.id),
                        )
                      }
                    />
                    {p.label} — {p.amount_minor / 100} {p.currency}
                  </label>
                ))}
              </div>
            )}

            {mode === "hourly" && (
              <div className="space-y-2 text-sm">
                <p className="text-neutral-500">
                  Amount = your saved hourly rate × hours (computed by the server).
                </p>
                {hourlyRows.map((r, i) => (
                  <div key={i} className="flex gap-2">
                    <input
                      value={r.label}
                      onChange={(e) =>
                        setHourlyRows(
                          hourlyRows.map((x, j) => (j === i ? { ...x, label: e.target.value } : x)),
                        )
                      }
                      className="flex-1 rounded border px-2 py-1"
                    />
                    <input
                      inputMode="numeric"
                      value={r.hours}
                      onChange={(e) =>
                        setHourlyRows(
                          hourlyRows.map((x, j) => (j === i ? { ...x, hours: e.target.value } : x)),
                        )
                      }
                      className="w-24 rounded border px-2 py-1"
                    />
                  </div>
                ))}
                {hourlyRows.length < 3 && (
                  <button
                    type="button"
                    onClick={() => setHourlyRows([...hourlyRows, { label: "", hours: "" }])}
                    className="text-accent"
                  >
                    + option
                  </button>
                )}
              </div>
            )}

            {mode === "fixed" && (
              <div className="flex gap-2 text-sm">
                <input
                  value={fixedLabel}
                  onChange={(e) => setFixedLabel(e.target.value)}
                  className="flex-1 rounded border px-2 py-1"
                />
                <input
                  inputMode="decimal"
                  placeholder="Amount"
                  value={fixedAmount}
                  onChange={(e) => setFixedAmount(e.target.value)}
                  className="w-32 rounded border px-2 py-1"
                />
              </div>
            )}
          </fieldset>

          {error && <p className="text-sm text-red-600">{error}</p>}
          <button
            type="submit"
            disabled={busy}
            className="rounded bg-accent px-4 py-2 text-white disabled:opacity-50"
          >
            {busy ? "Generating…" : "Generate"}
          </button>
        </form>
      </main>
    </>
  );
}
