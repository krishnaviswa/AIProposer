import { apiFetch, api, apiOrigin, API_BASE_URL, ApiError } from "@/lib/api";

describe("apiFetch", () => {
  const fetchMock = jest.fn();
  beforeEach(() => {
    fetchMock.mockReset();
    global.fetch = fetchMock as unknown as typeof fetch;
  });

  it("only ever calls the FastAPI base URL and attaches the bearer token", async () => {
    fetchMock.mockResolvedValue({ ok: true, status: 200, json: async () => ({ ok: 1 }) });

    await apiFetch("/me", {}, async () => "tok-123");

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe(`${API_BASE_URL}/me`);
    expect(url.startsWith("http://localhost:8000/v1")).toBe(true);
    expect((init.headers as Headers).get("Authorization")).toBe("Bearer tok-123");
  });

  it("omits Authorization when there is no session", async () => {
    fetchMock.mockResolvedValue({ ok: true, status: 200, json: async () => ({}) });
    await apiFetch("/me", {}, async () => null);
    const [, init] = fetchMock.mock.calls[0];
    expect((init.headers as Headers).has("Authorization")).toBe(false);
  });

  it("throws ApiError with the status and detail on a non-2xx", async () => {
    fetchMock.mockResolvedValue({
      ok: false,
      status: 402,
      json: async () => ({ detail: { error: "quota_exhausted" } }),
    });
    await expect(apiFetch("/proposals", { method: "POST" }, async () => "t")).rejects.toMatchObject({
      status: 402,
    });
    expect(new ApiError(402, "x")).toBeInstanceOf(Error);
  });

  it("getPdf hits the proposal pdf path and checkout posts the plan", async () => {
    fetchMock.mockResolvedValue({ ok: true, status: 200, json: async () => ({ pdf_url: "/uploads/x.pdf" }) });
    await api.getPdf("abc");
    expect(fetchMock.mock.calls[0][0]).toBe(`${API_BASE_URL}/proposals/abc/pdf`);

    fetchMock.mockResolvedValue({ ok: true, status: 200, json: async () => ({}) });
    await api.checkout("starter_inr");
    const [url, init] = fetchMock.mock.calls[1];
    expect(url).toBe(`${API_BASE_URL}/billing/checkout-session`);
    expect(JSON.parse(init.body)).toEqual({ plan_id: "starter_inr" });
  });

  it("apiOrigin strips the trailing /v1", () => {
    expect(apiOrigin()).toBe("http://localhost:8000");
  });
});
