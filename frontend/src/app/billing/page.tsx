"use client";

import { useState } from "react";
import Script from "next/script";

import { Nav } from "@/components/Nav";
import { api, ApiError } from "@/lib/api";
import { money } from "@/lib/format";
import { useResource } from "@/lib/useApi";
import type { MeView } from "@/lib/types";

// India Free -> Starter ₹500 / 20 (mvp-spec.md §5.1). One rail (Razorpay) in v0.
const STARTER = { id: "starter_inr", name: "Starter (India)", price_minor: 50000, included: 20 };

const CHECKOUT_JS = "https://checkout.razorpay.com/v1/checkout.js";

interface RazorpayFailure {
  error?: { description?: string; reason?: string };
}
interface RazorpayInstance {
  open: () => void;
  on: (event: "payment.failed", handler: (resp: RazorpayFailure) => void) => void;
}
declare global {
  interface Window {
    Razorpay?: new (options: Record<string, unknown>) => RazorpayInstance;
  }
}

export default function BillingPage() {
  const me = useResource<MeView>(() => api.getMe());
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState<string | null>(null);
  // AC 6: if Checkout.js fails to load we must still degrade cleanly.
  const [scriptFailed, setScriptFailed] = useState(false);

  function orderSummaryFallback(order: {
    provider_order_id: string;
    amount_paise: number;
    currency: string;
  }) {
    setNote(
      `Order ${order.provider_order_id} created for ${money(order.amount_paise, order.currency)}. ` +
        `Complete payment in Razorpay; your plan updates when the webhook is received.`,
    );
  }

  async function upgrade() {
    setBusy(true);
    setNote(null);
    try {
      const order = await api.checkout(STARTER.id);
      const key = process.env.NEXT_PUBLIC_RAZORPAY_KEY_ID || order.key_id;
      const hostedCheckout =
        typeof window !== "undefined" &&
        typeof window.Razorpay === "function" &&
        !!key &&
        !key.includes("mock") &&
        !scriptFailed;

      if (!hostedCheckout) {
        // Mock / placeholder key or Checkout.js unavailable (AC 6): the webhook
        // is what actually upgrades the plan.
        orderSummaryFallback(order);
        return;
      }

      const rzp = new window.Razorpay!({
        key,
        order_id: order.provider_order_id,
        // Amount comes straight from the server response — never computed here
        // (mvp-spec.md §0.3, §9).
        amount: order.amount_paise,
        currency: order.currency,
        name: "AIProposer",
        description: STARTER.name,
        handler: () => {
          // AC 3 / AC 8: the browser hand-off is UX only. Show a pending note and
          // re-read /v1/me once; the plan flips to Starter only after the webhook.
          setNote("Payment received — your plan updates in a moment.");
          me.refetch();
        },
        modal: {
          ondismiss: () => setNote("Checkout cancelled. Your plan is unchanged."),
        },
      });
      rzp.on("payment.failed", (resp) => {
        setNote(
          `Payment failed: ${resp?.error?.description ?? "please try again"}. Your plan is unchanged.`,
        );
        setBusy(false);
      });
      rzp.open();
    } catch (err) {
      setNote((err as ApiError).message);
    } finally {
      setBusy(false);
    }
  }

  const plan = me.data?.plan;
  const onStarter = plan?.id === STARTER.id;

  return (
    <>
      {/* AC 1: hosted Checkout.js — loaded on /billing only. */}
      <Script src={CHECKOUT_JS} strategy="afterInteractive" onError={() => setScriptFailed(true)} />
      <Nav />
      <main className="mx-auto max-w-xl px-4 py-8">
        <h1 className="mb-6 text-2xl font-semibold">Plan &amp; billing</h1>

        {me.data && (
          <p className="mb-6 text-sm text-neutral-600">
            Current plan: <strong>{plan?.name}</strong> — {me.data.usage.used}/{me.data.usage.included}{" "}
            proposals used this period.
          </p>
        )}

        <div className="rounded border bg-white p-5">
          <div className="flex items-baseline justify-between">
            <span className="font-medium">{STARTER.name}</span>
            <span className="text-lg">{money(STARTER.price_minor, "INR")}/mo</span>
          </div>
          <p className="mt-1 text-sm text-neutral-500">
            {STARTER.included} proposals per period · no watermark · follow-up email · pay via
            Razorpay (UPI / cards / netbanking).
          </p>
          <button
            onClick={upgrade}
            disabled={busy || onStarter}
            className="mt-4 rounded bg-accent px-4 py-2 text-sm text-white disabled:opacity-50"
          >
            {onStarter ? "You're on Starter" : busy ? "Starting checkout…" : "Upgrade to Starter"}
          </button>
        </div>

        {note && <p className="mt-4 text-sm text-neutral-700">{note}</p>}
      </main>
    </>
  );
}
