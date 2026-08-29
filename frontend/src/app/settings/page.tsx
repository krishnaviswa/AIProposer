"use client";

import { useEffect, useState } from "react";

import { Nav } from "@/components/Nav";
import { api } from "@/lib/api";
import { toMinor } from "@/lib/format";
import { useResource } from "@/lib/useApi";
import type { Currency, MeView } from "@/lib/types";

interface PkgRow {
  label: string;
  amount: string;
}

export default function SettingsPage() {
  const me = useResource<MeView>(() => api.getMe());
  const [currency, setCurrency] = useState<Currency>("INR");
  const [name, setName] = useState("");
  const [hourly, setHourly] = useState("");
  const [rows, setRows] = useState<PkgRow[]>([]);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!me.data) return;
    setCurrency(me.data.quote_currency as Currency);
    setName(me.data.name ?? "");
    setHourly(me.data.hourly_rate_minor ? String(me.data.hourly_rate_minor / 100) : "");
    setRows(
      me.data.packages.map((p) => ({ label: p.label, amount: String(p.amount_minor / 100) })),
    );
  }, [me.data]);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    const packages = [];
    for (const r of rows) {
      const amt = toMinor(r.amount);
      if (!r.label.trim() || amt === null) {
        setError("Each package needs a label and a valid amount.");
        return;
      }
      packages.push({ label: r.label.trim(), amount_minor: amt });
    }
    const rate = hourly.trim() ? toMinor(hourly) : null;
    try {
      const updated = await api.putMe({
        name: name || null,
        quote_currency: currency,
        hourly_rate_minor: rate,
        packages,
      });
      me.setData(updated);
      setSaved(true);
      setTimeout(() => setSaved(false), 1500);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <>
      <Nav />
      <main className="mx-auto max-w-2xl px-4 py-8">
        <h1 className="mb-6 text-2xl font-semibold">Your rates & packages</h1>
        <p className="mb-6 text-sm text-neutral-500">
          These numbers are the only prices that ever appear on a proposal. The AI never sets money.
        </p>

        <form onSubmit={save} className="space-y-5">
          <label className="block">
            <span className="text-sm">Display name</span>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="mt-1 w-full rounded border px-3 py-2"
            />
          </label>

          <label className="block">
            <span className="text-sm">Quote currency</span>
            <select
              value={currency}
              onChange={(e) => setCurrency(e.target.value as Currency)}
              className="mt-1 w-full rounded border px-3 py-2"
            >
              {(["INR", "USD", "EUR", "GBP"] as Currency[]).map((c) => (
                <option key={c}>{c}</option>
              ))}
            </select>
          </label>

          <label className="block">
            <span className="text-sm">Hourly rate ({currency}) — optional</span>
            <input
              inputMode="decimal"
              value={hourly}
              onChange={(e) => setHourly(e.target.value)}
              className="mt-1 w-full rounded border px-3 py-2"
              placeholder="e.g. 2500"
            />
          </label>

          <div>
            <span className="text-sm">Packages (up to 3)</span>
            <div className="mt-1 space-y-2">
              {rows.map((r, i) => (
                <div key={i} className="flex gap-2">
                  <input
                    placeholder="Label"
                    value={r.label}
                    onChange={(e) =>
                      setRows(rows.map((x, j) => (j === i ? { ...x, label: e.target.value } : x)))
                    }
                    className="flex-1 rounded border px-3 py-2"
                  />
                  <input
                    placeholder="Amount"
                    inputMode="decimal"
                    value={r.amount}
                    onChange={(e) =>
                      setRows(rows.map((x, j) => (j === i ? { ...x, amount: e.target.value } : x)))
                    }
                    className="w-32 rounded border px-3 py-2"
                  />
                  <button
                    type="button"
                    onClick={() => setRows(rows.filter((_, j) => j !== i))}
                    className="px-2 text-neutral-400 hover:text-red-600"
                  >
                    ✕
                  </button>
                </div>
              ))}
              {rows.length < 3 && (
                <button
                  type="button"
                  onClick={() => setRows([...rows, { label: "", amount: "" }])}
                  className="text-sm text-accent"
                >
                  + Add package
                </button>
              )}
            </div>
          </div>

          {error && <p className="text-sm text-red-600">{error}</p>}
          <button type="submit" className="rounded bg-accent px-4 py-2 text-white">
            {saved ? "Saved ✓" : "Save"}
          </button>
        </form>
      </main>
    </>
  );
}
