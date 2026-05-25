import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { OfferCard } from "./OfferCard";
import type { Offer } from "@/lib/types";

const baseOffer: Offer = {
  id: 42,
  price: 4.99,
  original_price: 7.15,
  discount_pct: 30,
  currency: "EUR",
  valid_from: "2026-05-20",
  valid_to: "2026-06-03",
  scraped_at: "2026-05-25T08:00:00Z",
  product: {
    id: 1,
    external_id: "p-1",
    name: "Φέτα ΠΟΠ Δωδώνη 400g",
    url: "https://www.ab.gr/p/1",
    image_url: null,
    category: "Τυριά",
    unit: "400g",
  },
  brand: {
    id: 1,
    name: "AB Βασιλόπουλος",
    slug: "ab",
    website_url: "https://www.ab.gr",
    country_code: "GR",
  },
};

describe("OfferCard", () => {
  it("renders product, brand, prices and discount badge", () => {
    render(<OfferCard offer={baseOffer} />);
    expect(screen.getByText("Φέτα ΠΟΠ Δωδώνη 400g")).toBeInTheDocument();
    expect(screen.getByText("AB Βασιλόπουλος")).toBeInTheDocument();
    expect(screen.getByText(/4,99/)).toBeInTheDocument();
    expect(screen.getByText(/7,15/)).toBeInTheDocument();
    expect(screen.getByText("-30%")).toBeInTheDocument();
  });

  it("hides original price when not discounted", () => {
    render(
      <OfferCard
        offer={{ ...baseOffer, original_price: null, discount_pct: null }}
      />,
    );
    expect(screen.queryByText(/7,15/)).not.toBeInTheDocument();
    expect(screen.queryByText(/-\d+%/)).not.toBeInTheDocument();
  });

  it("shows placeholder when image is missing", () => {
    const { container } = render(<OfferCard offer={baseOffer} />);
    // No <img>/<Image> rendered, just the placeholder emoji.
    expect(container.querySelector("img")).toBeNull();
  });

  it("links to the offer detail page", () => {
    render(<OfferCard offer={baseOffer} />);
    const link = screen.getByRole("link");
    expect(link).toHaveAttribute("href", "/offers/42");
  });

  it("renders the discount badge in the accent (French pink) palette", () => {
    // Guards the 60-30-10 palette: discount pills must use the accent
    // tokens. If anyone reintroduces rose-600 / red-500 / emerald-* etc.
    // here this assertion fails — and the eyeball pass would catch it
    // anyway, but tests are cheaper than humans. Neumorphism deliberately
    // does NOT apply to the discount pill — it's a signal, not a surface.
    render(<OfferCard offer={baseOffer} />);
    const badge = screen.getByText("-30%");
    expect(badge.className).toMatch(/\bbg-accent\b/);
    expect(badge.className).toMatch(/\btext-white\b/);
  });

  it("renders promo_label verbatim when set, overriding the raw -N% pill", () => {
    // Repro case: AB's "1+1 δώρο" deal. The offer carries no
    // discount_pct (the multi-buy maths is left to the consumer) but
    // does carry the brand's badge copy. We must render the label.
    render(
      <OfferCard
        offer={{
          ...baseOffer,
          original_price: null,
          discount_pct: null,
          promo_label: "1+1 δώρο",
          promo_type: "bxgy_free",
        }}
      />,
    );
    const badge = screen.getByText("1+1 δώρο");
    expect(badge.className).toMatch(/\bbg-accent\b/);
    expect(badge.className).toMatch(/\btext-white\b/);
    // The numeric pill must NOT also render — promo_label takes priority.
    expect(screen.queryByText(/^-\d+%$/)).not.toBeInTheDocument();
  });

  it("prefers promo_label over discount_pct when both are present", () => {
    // SHT offers carry both. Brand-supplied copy ("Κέρδος 15%") is more
    // precise than our reconstructed "-15%".
    render(
      <OfferCard
        offer={{
          ...baseOffer,
          discount_pct: 15,
          promo_label: "Κέρδος 15%",
          promo_type: "strikethrough",
        }}
      />,
    );
    expect(screen.getByText("Κέρδος 15%")).toBeInTheDocument();
    expect(screen.queryByText("-15%")).not.toBeInTheDocument();
  });

  it("falls back to -N% when promo_label is null but discount_pct is set", () => {
    // Pre-promo-label API response: promo_label undefined / null,
    // discount_pct still present. The legacy pill must still render.
    render(
      <OfferCard
        offer={{
          ...baseOffer,
          promo_label: null,
        }}
      />,
    );
    expect(screen.getByText("-30%")).toBeInTheDocument();
  });

  it("uses the neumorphism raised surface on the card root", () => {
    // Regression guard for the neumorphism layer: the card sits on the
    // shared canvas (no tinted surface, no border) and carries the raised
    // two-tone shadow. If a future theme pass reintroduces a flat card or
    // a hard border, this test fails before the eyeball pass would.
    render(<OfferCard offer={baseOffer} />);
    const link = screen.getByRole("link");
    expect(link.className).toMatch(/\bshadow-raised\b/);
    expect(link.className).toMatch(/\bbg-canvas\b/);
    expect(link.className).not.toMatch(/\bborder-border\b/);
  });
});
