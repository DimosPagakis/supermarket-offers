import { describe, expect, it, vi, beforeEach } from "vitest";
import { act, renderHook } from "@testing-library/react";
import { toggleInCsv, useUrlFilters } from "./use-url-filters";

const pushSpy = vi.fn();
let currentSearch = "";

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: pushSpy,
    replace: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
    refresh: vi.fn(),
    prefetch: vi.fn(),
  }),
  usePathname: () => "/compare",
  useSearchParams: () => new URLSearchParams(currentSearch),
}));

beforeEach(() => {
  pushSpy.mockReset();
  currentSearch = "";
});

describe("toggleInCsv", () => {
  it("adds a value when absent", () => {
    expect(toggleInCsv("", "ab")).toBe("ab");
    expect(toggleInCsv(null, "ab")).toBe("ab");
    expect(toggleInCsv("lidl", "ab")).toBe("lidl,ab");
  });

  it("removes a value when present", () => {
    expect(toggleInCsv("lidl,ab", "ab")).toBe("lidl");
    expect(toggleInCsv("ab", "ab")).toBe("");
  });

  it("trims whitespace and ignores empty members", () => {
    expect(toggleInCsv(" ab , , lidl ", "mymarket")).toBe("ab,lidl,mymarket");
  });
});

describe("useUrlFilters", () => {
  it("pushes a scroll-stable URL when updateParam adds a key", () => {
    const { result } = renderHook(() => useUrlFilters());

    act(() => {
      result.current.updateParam((sp) => sp.set("brand", "lidl"));
    });

    expect(pushSpy).toHaveBeenCalledTimes(1);
    expect(pushSpy).toHaveBeenCalledWith("/compare?brand=lidl", {
      scroll: false,
    });
  });

  it("always clears `page` on every updateParam call", () => {
    currentSearch = "brand=lidl&page=4";
    const { result } = renderHook(() => useUrlFilters());

    act(() => {
      result.current.updateParam((sp) => sp.set("category", "Snacks"));
    });

    expect(pushSpy).toHaveBeenCalledTimes(1);
    const [url] = pushSpy.mock.calls[0];
    // brand survives, category was added, page=4 was wiped.
    expect(url).toContain("brand=lidl");
    expect(url).toContain("category=Snacks");
    expect(url).not.toContain("page=");
  });

  it("composes rapid clicks through the pending ref", () => {
    const { result } = renderHook(() => useUrlFilters());

    act(() => {
      result.current.updateParam((sp) => sp.set("brand", "lidl"));
      result.current.updateParam((sp) => sp.set("min_brands", "3"));
    });

    expect(pushSpy).toHaveBeenCalledTimes(2);
    // The second push must include the first edit — that's the whole
    // point of `pendingSearchRef`. If the ref weren't synchronous the
    // second call would clobber `brand=lidl`.
    expect(pushSpy.mock.calls[1][0]).toBe("/compare?brand=lidl&min_brands=3");
  });

  it("reset wipes every key by default except `q`", () => {
    currentSearch =
      "q=feta&brand=lidl&category=Snacks&min_brands=3&sort=display_name";
    const { result } = renderHook(() => useUrlFilters());

    act(() => {
      result.current.reset();
    });

    expect(pushSpy).toHaveBeenCalledTimes(1);
    expect(pushSpy).toHaveBeenCalledWith("/compare?q=feta", { scroll: false });
  });

  it("reset honours a custom preserveOnReset list", () => {
    currentSearch = "q=feta&brand=lidl&category=Snacks";
    const { result } = renderHook(() =>
      useUrlFilters({ preserveOnReset: ["category"] }),
    );

    act(() => {
      result.current.reset();
    });

    expect(pushSpy).toHaveBeenCalledTimes(1);
    expect(pushSpy).toHaveBeenCalledWith("/compare?category=Snacks", {
      scroll: false,
    });
  });

  it("emits an empty path when every param is cleared", () => {
    currentSearch = "brand=lidl";
    const { result } = renderHook(() => useUrlFilters({ preserveOnReset: [] }));

    act(() => {
      result.current.reset();
    });

    expect(pushSpy).toHaveBeenCalledTimes(1);
    // No trailing `?` when there is nothing to encode — pins the URL
    // contract the filter-bar test asserts.
    expect(pushSpy).toHaveBeenCalledWith("/compare", { scroll: false });
  });
});
