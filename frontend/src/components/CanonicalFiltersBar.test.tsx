import { describe, expect, it, vi, beforeEach } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { CanonicalFiltersBar } from "./CanonicalFiltersBar";
import type { Brand } from "@/lib/types";

// `next/navigation` is mocked at module level so the bar's hooks resolve to
// our spies. The router spy lets us assert which URL the bar pushed and the
// `searchParams` spy lets each test seed an initial URL state.

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

const brands: Brand[] = [
  {
    id: 1,
    name: "AB Vassilopoulos",
    slug: "ab",
    website_url: "https://www.ab.gr",
    country_code: "GR",
  },
  {
    id: 2,
    name: "Lidl Hellas",
    slug: "lidl",
    website_url: "https://www.lidl-hellas.gr",
    country_code: "GR",
  },
];

beforeEach(() => {
  pushSpy.mockReset();
  currentSearch = "";
  // jsdom provides a `window.location`; we have to keep it aligned with
  // `currentSearch` so the bar's pendingSearchRef bootstraps from the right
  // base URL.
  window.history.replaceState({}, "", "/compare");
});

describe("CanonicalFiltersBar", () => {
  it("pushes ?brand=lidl when the Lidl chip is clicked from a clean URL", () => {
    render(
      <CanonicalFiltersBar brands={brands} categories={["Snacks"]} maxBrands={5} />,
    );

    fireEvent.click(screen.getByRole("button", { name: /Lidl Hellas/ }));

    expect(pushSpy).toHaveBeenCalledTimes(1);
    expect(pushSpy).toHaveBeenCalledWith("/compare?brand=lidl", { scroll: false });
  });

  it("toggles a brand off when clicked again", () => {
    currentSearch = "brand=lidl";
    window.history.replaceState({}, "", "/compare?brand=lidl");
    render(
      <CanonicalFiltersBar brands={brands} categories={["Snacks"]} maxBrands={5} />,
    );

    fireEvent.click(screen.getByRole("button", { name: /Lidl Hellas/ }));

    expect(pushSpy).toHaveBeenCalledWith("/compare", { scroll: false });
  });

  it("sets min_brands=3 and preserves an existing brand filter", () => {
    currentSearch = "brand=lidl";
    window.history.replaceState({}, "", "/compare?brand=lidl");
    render(
      <CanonicalFiltersBar brands={brands} categories={["Snacks"]} maxBrands={5} />,
    );

    fireEvent.click(screen.getByRole("button", { name: "3", pressed: false }));

    expect(pushSpy).toHaveBeenCalledTimes(1);
    const [url, opts] = pushSpy.mock.calls[0];
    expect(opts).toEqual({ scroll: false });
    expect(url).toBe("/compare?brand=lidl&min_brands=3");
  });

  it("clears every filter except q on reset", () => {
    currentSearch = "q=feta&brand=lidl&category=Snacks&min_brands=3&sort=display_name&dir=asc";
    window.history.replaceState({}, "", `/compare?${currentSearch}`);
    render(
      <CanonicalFiltersBar brands={brands} categories={["Snacks"]} maxBrands={5} />,
    );

    fireEvent.click(screen.getByRole("button", { name: /Καθαρισμός/ }));

    expect(pushSpy).toHaveBeenCalledTimes(1);
    expect(pushSpy).toHaveBeenCalledWith("/compare?q=feta", { scroll: false });
  });

  it("emits each click as a separate router.push so back/forward step through the history", () => {
    // We assert each click pushes once, in order. We deliberately don't
    // assert that the SECOND push includes the first push's diff — in jsdom
    // the mocked `useSearchParams` never re-commits, so the bar's
    // pending-URL effect snaps back between clicks. The composition
    // behaviour is verified end-to-end in the Playwright smoke (see PR
    // description), where Next actually advances `searchParams` between
    // clicks within a transition.
    render(
      <CanonicalFiltersBar brands={brands} categories={["Snacks"]} maxBrands={5} />,
    );

    fireEvent.click(screen.getByRole("button", { name: /Lidl Hellas/ }));
    fireEvent.click(screen.getByRole("button", { name: "3", pressed: false }));

    expect(pushSpy).toHaveBeenCalledTimes(2);
    expect(pushSpy.mock.calls[0][0]).toBe("/compare?brand=lidl");
    expect(pushSpy.mock.calls[0][1]).toEqual({ scroll: false });
    expect(pushSpy.mock.calls[1][1]).toEqual({ scroll: false });
  });
});
