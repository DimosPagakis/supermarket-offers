import { describe, expect, it } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { FamilyVariantRow } from "./FamilyVariantRow";
import type { FamilyVariant } from "@/lib/types";

const ab = {
  id: 1,
  name: "AB Βασιλόπουλος",
  slug: "ab",
  website_url: "https://www.ab.gr",
  country_code: "GR",
};
const sk = {
  id: 2,
  name: "Σκλαβενίτης",
  slug: "sklavenitis",
  website_url: "https://www.sklavenitis.gr",
  country_code: "GR",
};

function buildVariant(overrides: Partial<FamilyVariant> = {}): FamilyVariant {
  return {
    variant_descriptor: "africa",
    products: [
      {
        id: 100,
        external_id: "AB-771",
        name: "Axe Αποσμητικό Σπρέι Africa 150ml",
        url: "https://www.ab.gr/p/100",
        image_url: null,
        brand: ab,
        offer: {
          id: 1000,
          price: 2.5,
          original_price: 3.1,
          discount_pct: 19,
          valid_from: "2026-05-20",
          valid_to: "2026-06-10",
          scraped_at: "2026-05-25T08:00:00Z",
        },
      },
      {
        id: 200,
        external_id: "SK-883",
        name: "AXE Αποσμητικό Σπρέι Africa 150ml",
        url: "https://www.sklavenitis.gr/p/200",
        image_url: null,
        brand: sk,
        offer: {
          id: 1001,
          price: 2.8,
          original_price: null,
          discount_pct: null,
          valid_from: "2026-05-20",
          valid_to: "2026-06-10",
          scraped_at: "2026-05-25T08:00:00Z",
        },
      },
    ],
    min_price: 2.5,
    max_price: 2.8,
    cheapest_brand: { id: ab.id, name: ab.name, slug: ab.slug },
    ...overrides,
  };
}

describe("FamilyVariantRow", () => {
  it("renders the descriptor as a row title and shows per-chain offers", () => {
    render(<FamilyVariantRow variant={buildVariant()} />);

    expect(screen.getByRole("heading", { level: 3 })).toHaveTextContent("Africa");
    // "AB Βασιλόπουλος" appears twice — once as the cheapest-brand
    // marker in the header, once on its own list item — getAllByText
    // accepts both.
    expect(screen.getAllByText(/AB Βασιλόπουλος/).length).toBeGreaterThan(0);
    expect(screen.getByText("Σκλαβενίτης")).toBeInTheDocument();
    // Both chain prices show. 2,50 also appears in the header
    // "from price" — getAllByText accepts duplicates.
    expect(screen.getAllByText(/2,50/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/2,80/).length).toBeGreaterThan(0);
  });

  it("highlights the cheapest brand and per-row discount", () => {
    render(<FamilyVariantRow variant={buildVariant()} />);

    // Cheapest brand surfaces in the header — the `from XYZ στην NAME`
    // copy renders the brand name inside a styled span.
    const header = screen.getByRole("heading", { level: 3 });
    const headerCopy = header.parentElement?.textContent ?? "";
    expect(headerCopy).toMatch(/στην/);
    expect(headerCopy).toContain("AB Βασιλόπουλος");
    // -19% chip from the discount on AB's row.
    expect(screen.getByText(/-19%/)).toBeInTheDocument();
  });

  it("renders products in ascending price order (cheapest first)", () => {
    render(<FamilyVariantRow variant={buildVariant()} />);

    // The "per-chain mini comparison" list is the only <ul> inside
    // the variant row — the article itself is a <li> in the parent
    // page. Grab the inner list directly.
    const list = screen.getByTestId("family-variant-row").querySelector("ul");
    expect(list).not.toBeNull();
    const items = within(list!).getAllByRole("listitem");
    const first = within(items[0]);
    expect(first.getByText("AB Βασιλόπουλος")).toBeInTheDocument();
    const second = within(items[1]);
    expect(second.getByText("Σκλαβενίτης")).toBeInTheDocument();
  });

  it("renders 'Χωρίς παραλλαγή' bucket for the —-descriptor", () => {
    const variant = buildVariant({
      variant_descriptor: "—",
      products: [
        {
          id: 9,
          external_id: null,
          name: "Generic 150ml",
          url: null,
          image_url: null,
          brand: ab,
          offer: null,
        },
      ],
      min_price: null,
      max_price: null,
      cheapest_brand: null,
    });

    render(<FamilyVariantRow variant={variant} />);

    expect(screen.getByText("Χωρίς παραλλαγή")).toBeInTheDocument();
  });
});
