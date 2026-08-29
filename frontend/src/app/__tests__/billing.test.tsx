import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import BillingPage from "@/app/billing/page";

jest.mock("next/navigation", () => ({ useRouter: () => ({ push: jest.fn() }) }));

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
});

it("shows the current plan and the Starter offer", async () => {
  render(<BillingPage />);
  expect(await screen.findByText(/Current plan:/)).toHaveTextContent("Free");
  expect(screen.getByText("₹500/mo")).toBeInTheDocument();
});

it("Upgrade calls the checkout API and (mock key) shows the order note", async () => {
  render(<BillingPage />);
  await screen.findByText(/Current plan:/);
  await userEvent.click(screen.getByRole("button", { name: /Upgrade to Starter/ }));

  expect(checkout).toHaveBeenCalledWith("starter_inr");
  expect(await screen.findByText(/Order order_mock_1 created/)).toBeInTheDocument();
});
