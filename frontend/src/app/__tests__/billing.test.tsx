import fs from "fs";
import path from "path";

import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import BillingPage from "@/app/billing/page";

jest.mock("next/navigation", () => ({ useRouter: () => ({ push: jest.fn() }) }));
// Checkout.js must never actually load under jsdom (AC 14).
jest.mock("next/script", () => ({
  __esModule: true,
  default: () => null,
}));

const getMe = jest.fn();
const checkout = jest.fn();
jest.mock("@/lib/api", () => ({
  api: {
    getMe: (...a: unknown[]) => getMe(...a),
    checkout: (...a: unknown[]) => checkout(...a),
  },
  ApiError: class extends Error {},
}));

beforeEach(() => {
  getMe.mockResolvedValue({
    plan: { id: "free", name: "Free", proposals_included: 3 },
    usage: { included: 3, used: 3, remaining: 0, period_end: "2026-09-29T00:00:00Z" },
  });
  checkout.mockResolvedValue({
    provider_order_id: "order_mock_1",
    key_id: "rzp_test_mock",
    amount_paise: 50000,
    currency: "INR",
    plan_id: "starter_inr",
  });
  delete process.env.NEXT_PUBLIC_RAZORPAY_KEY_ID;
  delete (window as { Razorpay?: unknown }).Razorpay;
});

it("shows the current plan and the Starter offer", async () => {
  render(<BillingPage />);
  expect(await screen.findByText(/Current plan:/)).toHaveTextContent("Free");
  expect(screen.getByText("₹500/mo")).toBeInTheDocument();
});

it("hosted Checkout.js is loaded on /billing only — no other route references it (AC 1)", () => {
  const appDir = path.join(__dirname, "..");
  const hits: string[] = [];
  const walk = (dir: string) => {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      const full = path.join(dir, entry.name);
      if (entry.isDirectory()) {
        if (entry.name === "__tests__") continue;
        walk(full);
      } else if (/\.(tsx?|jsx?)$/.test(entry.name)) {
        if (fs.readFileSync(full, "utf8").includes("checkout.razorpay.com")) {
          hits.push(path.relative(appDir, full).replace(/\\/g, "/"));
        }
      }
    }
  };
  walk(appDir);
  expect(hits).toEqual(["billing/page.tsx"]);
});

it("mock key / no Checkout.js -> order-summary fallback, no crash (AC 6)", async () => {
  render(<BillingPage />);
  await screen.findByText(/Current plan:/);
  await userEvent.click(screen.getByRole("button", { name: /Upgrade to Starter/ }));

  expect(checkout).toHaveBeenCalledWith("starter_inr");
  expect(await screen.findByText(/Order order_mock_1 created/)).toBeInTheDocument();
});

/**
 * With a real key + a fake window.Razorpay, the hosted modal path runs. We drive
 * the handler / ondismiss / payment.failed callbacks Razorpay would normally fire.
 */
function installFakeRazorpay() {
  const calls: { options: Record<string, unknown>; failHandlers: Array<(r: unknown) => void> } = {
    options: {},
    failHandlers: [],
  };
  process.env.NEXT_PUBLIC_RAZORPAY_KEY_ID = "rzp_live_real";
  (window as { Razorpay?: unknown }).Razorpay = function (this: unknown, options: Record<string, unknown>) {
    calls.options = options;
    return {
      open: jest.fn(),
      on: (_event: string, handler: (r: unknown) => void) => calls.failHandlers.push(handler),
    };
  } as unknown as Window["Razorpay"];
  return calls;
}

it("success handler -> pending note + a single /v1/me refetch, no client-side plan flip (AC 3, 8)", async () => {
  const rzp = installFakeRazorpay();
  render(<BillingPage />);
  await screen.findByText(/Current plan:/);

  const checkoutBefore = checkout.mock.calls.length;
  await userEvent.click(screen.getByRole("button", { name: /Upgrade to Starter/ }));
  // amount + currency handed to Razorpay are the server values, untouched (AC 2).
  expect(rzp.options.amount).toBe(50000);
  expect(rzp.options.currency).toBe("INR");
  expect(rzp.options.order_id).toBe("order_mock_1");
  // exactly one checkout-session call for the whole flow (AC 2 / AC 7).
  expect(checkout.mock.calls.length).toBe(checkoutBefore + 1);

  const before = getMe.mock.calls.length;
  await act(async () => {
    (rzp.options.handler as () => void)();
  });
  expect(await screen.findByText(/plan updates in a moment/i)).toBeInTheDocument();
  expect(getMe.mock.calls.length).toBe(before + 1); // one refetch, not a poll
  expect(screen.getByText(/Current plan:/)).toHaveTextContent("Free"); // no optimistic flip
});

it("modal dismiss -> neutral cancelled note, plan unchanged (AC 4)", async () => {
  const rzp = installFakeRazorpay();
  render(<BillingPage />);
  await screen.findByText(/Current plan:/);
  await userEvent.click(screen.getByRole("button", { name: /Upgrade to Starter/ }));

  await act(async () => {
    (rzp.options.modal as { ondismiss: () => void }).ondismiss();
  });
  expect(await screen.findByText(/Checkout cancelled/i)).toBeInTheDocument();
  expect(screen.getByText(/Current plan:/)).toHaveTextContent("Free");
});

it("payment.failed -> error note with the reason, button back to idle (AC 5)", async () => {
  const rzp = installFakeRazorpay();
  render(<BillingPage />);
  await screen.findByText(/Current plan:/);
  await userEvent.click(screen.getByRole("button", { name: /Upgrade to Starter/ }));

  await act(async () => {
    rzp.failHandlers.forEach((h) => h({ error: { description: "card declined" } }));
  });
  expect(await screen.findByText(/Payment failed: card declined/i)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /Upgrade to Starter/ })).toBeEnabled();
});
