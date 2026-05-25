import { describe, expect, it } from "vitest";
import { brandColour } from "./brand-colours";

/**
 * The fallback contract is architecturally load-bearing — every card
 * meta row, every chip, and the filter bars all consume `brandColour`
 * directly. A new chain seeded backend-side must render *something*
 * coherent even before design has chosen a tint. See
 * docs/architecture/brand-colour-fallback.md.
 */
describe("brandColour", () => {
  it("returns the seeded palette entry for a known slug", () => {
    const ab = brandColour("ab");
    expect(ab).toEqual({ bg: "#FDE4E6", fg: "#9B0512", ring: "#E30613" });
  });

  it("returns the soft Picton fallback for an unknown slug", () => {
    // Regression guard: must never return `undefined`. The frontend
    // styles brand chips inline with these hex values; a missing entry
    // would crash rendering rather than degrade gracefully.
    const unknown = brandColour("brand-that-doesnt-exist-yet");
    expect(unknown).toBeDefined();
    expect(unknown).toMatchObject({
      bg: expect.stringMatching(/^#[0-9A-Fa-f]{6}$/),
      fg: expect.stringMatching(/^#[0-9A-Fa-f]{6}$/),
      ring: expect.stringMatching(/^#[0-9A-Fa-f]{6}$/),
    });
  });

  it("returns the same fallback object for every unknown slug", () => {
    // Cheap stability check — if a future refactor accidentally
    // computes a per-slug fallback, the brand grid would shimmer
    // between renders. Pin the contract.
    const a = brandColour("unknown-one");
    const b = brandColour("unknown-two");
    expect(a).toEqual(b);
  });
});
