import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { buildOfferQueryString } from "./api";

describe("buildOfferQueryString", () => {
  it("returns empty when no params provided", () => {
    expect(buildOfferQueryString({})).toBe("");
  });

  it("serialises brand and category as csv", () => {
    expect(
      buildOfferQueryString({ brand: ["ab", "lidl"], category: ["Τυριά"] }),
    ).toBe("?brand=ab%2Clidl&category=%CE%A4%CF%85%CF%81%CE%B9%CE%AC");
  });

  it("includes pagination and sort", () => {
    const qs = buildOfferQueryString({
      sort: "price",
      dir: "asc",
      page: 3,
      per_page: 20,
    });
    expect(qs).toBe("?sort=price&dir=asc&page=3&per_page=20");
  });

  it("emits booleans as strings", () => {
    expect(buildOfferQueryString({ has_discount: true })).toBe(
      "?has_discount=true",
    );
  });

  it("skips empty arrays", () => {
    expect(buildOfferQueryString({ brand: [] })).toBe("");
  });
});

describe("fetchOffers (real backend path)", () => {
  let originalFetch: typeof globalThis.fetch;

  beforeEach(() => {
    originalFetch = globalThis.fetch;
    // Make sure the mock-mode env var is not set so we exercise the
    // real fetch path. Vitest runs in node, NEXT_PUBLIC_USE_MOCKS is
    // unset by default.
    delete (process.env as Record<string, string | undefined>)
      .NEXT_PUBLIC_USE_MOCKS;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it("calls the public v1 endpoint and parses the envelope", async () => {
    const mockResponse = {
      data: [],
      meta: { current_page: 1, per_page: 50, total: 0, last_page: 1 },
      links: {
        first: "/api/public/v1/offers?page=1",
        last: "/api/public/v1/offers?page=1",
        next: null,
        prev: null,
        self: "/api/public/v1/offers?page=1",
      },
    };
    const fetchSpy = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(mockResponse), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    globalThis.fetch = fetchSpy as unknown as typeof globalThis.fetch;

    const { fetchOffers } = await import("./api");
    const result = await fetchOffers({ brand: ["ab"], min_discount: 20 });

    expect(fetchSpy).toHaveBeenCalledTimes(1);
    const [url] = fetchSpy.mock.calls[0];
    expect(url).toMatch(/\/api\/public\/v1\/offers\?/);
    expect(url).toContain("brand=ab");
    expect(url).toContain("min_discount=20");
    expect(result).toEqual(mockResponse);
  });

  it("throws on non-2xx responses", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(
      new Response("nope", { status: 500, statusText: "Server Error" }),
    ) as unknown as typeof globalThis.fetch;

    const { fetchOffers } = await import("./api");
    await expect(fetchOffers()).rejects.toThrow(/500/);
  });
});
