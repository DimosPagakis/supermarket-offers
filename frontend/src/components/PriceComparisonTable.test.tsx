import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { PriceComparisonTable } from "./PriceComparisonTable";
import type { CanonicalOffer } from "@/lib/types";

function makeOffer(
  brandSlug: string,
  brandName: string,
  price: number,
  opts: Partial<{ originalPrice: number; discountPct: number }> = {},
): CanonicalOffer {
  return {
    brand: {
      id: brandSlug.length,
      name: brandName,
      slug: brandSlug,
      website_url: `https://www.${brandSlug}.gr`,
      country_code: "GR",
    },
    product: {
      id: brandSlug.length * 100,
      name: `${brandName} Lacta 31g`,
      url: `https://www.${brandSlug}.gr/p/lacta-31g`,
      image_url: null,
    },
    offer: {
      id: brandSlug.length * 1000,
      price,
      original_price: opts.originalPrice ?? null,
      discount_pct: opts.discountPct ?? null,
      valid_from: "2026-05-25",
      valid_to: "2026-06-03",
      scraped_at: "2026-05-25T08:00:00Z",
    },
  };
}

describe("PriceComparisonTable", () => {
  it("renders one row per offer with brand and price", () => {
    const offers = [
      makeOffer("ab", "AB Βασιλόπουλος", 0.69, {
        originalPrice: 0.85,
        discountPct: 19,
      }),
      makeOffer("mymarket", "My Market", 0.75),
      makeOffer("sklavenitis", "Σκλαβενίτης", 0.79, {
        originalPrice: 0.85,
        discountPct: 7,
      }),
    ];

    render(<PriceComparisonTable offers={offers} />);

    expect(screen.getByText("AB Βασιλόπουλος")).toBeInTheDocument();
    expect(screen.getByText("My Market")).toBeInTheDocument();
    expect(screen.getByText("Σκλαβενίτης")).toBeInTheDocument();
    expect(screen.getByText(/0,69/)).toBeInTheDocument();
    expect(screen.getByText(/0,75/)).toBeInTheDocument();
    expect(screen.getByText(/0,79/)).toBeInTheDocument();
  });

  it("highlights only the cheapest row", () => {
    const offers = [
      makeOffer("ab", "AB Βασιλόπουλος", 0.69),
      makeOffer("mymarket", "My Market", 0.75),
      makeOffer("sklavenitis", "Σκλαβενίτης", 0.79),
    ];

    render(<PriceComparisonTable offers={offers} />);

    const stars = screen.getAllByLabelText("Φθηνότερη τιμή");
    expect(stars).toHaveLength(1);

    // Cheapest row should sit in the same row as AB.
    const star = stars[0];
    const row = star.closest("tr");
    expect(row).not.toBeNull();
    expect(row!.textContent).toContain("AB Βασιλόπουλος");
    expect(row!.textContent).toContain("0,69");
  });

  it("marks every tied row when prices are equal", () => {
    const offers = [
      makeOffer("ab", "AB Βασιλόπουλος", 0.79),
      makeOffer("mymarket", "My Market", 0.79),
    ];
    render(<PriceComparisonTable offers={offers} />);
    expect(screen.getAllByLabelText("Φθηνότερη τιμή")).toHaveLength(2);
  });

  it("renders the empty state cleanly when no offers", () => {
    render(<PriceComparisonTable offers={[]} />);
    expect(screen.queryByRole("table")).toBeNull();
    expect(
      screen.getByText(/Δεν υπάρχουν ενεργές προσφορές/),
    ).toBeInTheDocument();
  });

  it("renders defensively with a single-member canonical (no crash, no star ambiguity)", () => {
    const offers = [makeOffer("ab", "AB Βασιλόπουλος", 0.69)];
    render(<PriceComparisonTable offers={offers} />);
    expect(screen.getByText("AB Βασιλόπουλος")).toBeInTheDocument();
    // The single row is by definition the cheapest.
    expect(screen.getAllByLabelText("Φθηνότερη τιμή")).toHaveLength(1);
  });
});
