import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import SignInPage from "@/app/sign-in/page";

const signInWithPassword = jest.fn();
const signInWithOAuth = jest.fn();
const signInWithOtp = jest.fn();
const verifyOtp = jest.fn();
jest.mock("@/lib/supabase/client", () => ({
  createClient: () => ({
    auth: {
      signInWithPassword: (...a: unknown[]) => signInWithPassword(...a),
      signInWithOAuth: (...a: unknown[]) => signInWithOAuth(...a),
      signInWithOtp: (...a: unknown[]) => signInWithOtp(...a),
      verifyOtp: (...a: unknown[]) => verifyOtp(...a),
    },
  }),
}));

const realLocation = window.location;
function stubLocation(search = "") {
  Object.defineProperty(window, "location", {
    configurable: true,
    value: {
      origin: "http://localhost:3000",
      href: "http://localhost:3000/sign-in",
      search,
      assign: jest.fn(),
    },
  });
}
const assignMock = () => window.location.assign as jest.Mock;

beforeEach(() => {
  signInWithPassword.mockResolvedValue({ error: null });
  signInWithOAuth.mockResolvedValue({ error: null });
  signInWithOtp.mockResolvedValue({ error: null });
  verifyOtp.mockResolvedValue({ error: null });
  stubLocation();
});
afterEach(() => {
  Object.defineProperty(window, "location", { configurable: true, value: realLocation });
  delete process.env.NEXT_PUBLIC_AUTH_PHONE_OTP;
  jest.clearAllMocks();
});

it("Google sign-in redirects through /auth/callback, not / (AC 12)", async () => {
  render(<SignInPage />);
  await userEvent.click(screen.getByRole("button", { name: /Continue with Google/ }));

  expect(signInWithOAuth).toHaveBeenCalledWith(
    expect.objectContaining({
      provider: "google",
      options: { redirectTo: "http://localhost:3000/auth/callback" },
    }),
  );
});

it("email/password success hard-navigates to /auth/callback so the handler runs", async () => {
  render(<SignInPage />);
  await userEvent.type(screen.getByPlaceholderText("you@example.com"), "a@b.com");
  await userEvent.type(screen.getByPlaceholderText("Password"), "pw123456");
  await userEvent.click(screen.getByRole("button", { name: /^Continue$/ }));

  expect(signInWithPassword).toHaveBeenCalledWith({ email: "a@b.com", password: "pw123456" });
  expect(assignMock()).toHaveBeenCalledWith("/auth/callback");
});

it("shows the error bounced back from /auth/callback as ?error=", async () => {
  stubLocation("?error=Could%20not%20sign%20you%20in");
  render(<SignInPage />);
  expect(await screen.findByText(/Could not sign you in/)).toBeInTheDocument();
});

it("a failed password sign-in shows the message and does not navigate", async () => {
  signInWithPassword.mockResolvedValue({ error: { message: "Invalid login credentials" } });
  render(<SignInPage />);
  await userEvent.type(screen.getByPlaceholderText("you@example.com"), "a@b.com");
  await userEvent.type(screen.getByPlaceholderText("Password"), "wrongpw");
  await userEvent.click(screen.getByRole("button", { name: /^Continue$/ }));

  expect(await screen.findByText(/Invalid login credentials/)).toBeInTheDocument();
  expect(assignMock()).not.toHaveBeenCalled();
});

it("hides the phone option by default (S-002 parity: email + Google only)", () => {
  render(<SignInPage />);
  expect(screen.getByPlaceholderText("you@example.com")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /Continue with Google/ })).toBeInTheDocument();
  expect(screen.queryByText(/sign in with your phone/i)).not.toBeInTheDocument();
});

it("shows the phone OTP flow when NEXT_PUBLIC_AUTH_PHONE_OTP=true, then lands on /auth/callback", async () => {
  process.env.NEXT_PUBLIC_AUTH_PHONE_OTP = "true";
  render(<SignInPage />);

  await userEvent.type(screen.getByPlaceholderText("+91 90000 00000"), "+919000000000");
  await userEvent.click(screen.getByRole("button", { name: /Send code/ }));
  expect(signInWithOtp).toHaveBeenCalledWith({ phone: "+919000000000" });

  await userEvent.type(await screen.findByPlaceholderText("6-digit code"), "123456");
  await userEvent.click(screen.getByRole("button", { name: /Verify & continue/ }));
  expect(verifyOtp).toHaveBeenCalledWith({ phone: "+919000000000", token: "123456", type: "sms" });
  // Same funnel as every other sign-in path (ADR-004).
  expect(assignMock()).toHaveBeenCalledWith("/auth/callback");
});
