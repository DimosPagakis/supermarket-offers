import type {
  Brand,
  CanonicalOffer,
  CanonicalProductDetail,
  CanonicalProductSummary,
  Offer,
} from "@/lib/types";

export const mockBrands: Brand[] = [
  {
    id: 1,
    name: "AB Βασιλόπουλος",
    slug: "ab",
    website_url: "https://www.ab.gr",
    country_code: "GR",
  },
  {
    id: 2,
    name: "Σκλαβενίτης",
    slug: "sklavenitis",
    website_url: "https://www.sklavenitis.gr",
    country_code: "GR",
  },
  {
    id: 3,
    name: "Lidl Hellas",
    slug: "lidl",
    website_url: "https://www.lidl-hellas.gr",
    country_code: "GR",
  },
  {
    id: 4,
    name: "My Market",
    slug: "mymarket",
    website_url: "https://www.mymarket.gr",
    country_code: "GR",
  },
  {
    id: 5,
    name: "Μασούτης",
    slug: "masoutis",
    website_url: "https://www.masoutis.gr",
    country_code: "GR",
  },
];

export const mockCategories: string[] = [
  "Τυριά",
  "Φρέσκα",
  "Κρέατα",
  "Ψάρια",
  "Φρούτα",
  "Λαχανικά",
  "Ποτά",
  "Γαλακτοκομικά",
  "Καθαριστικά",
  "Καλλυντικά",
];

type ProductSeed = {
  name: string;
  category: string;
  unit: string;
  price: number;
  original?: number;
};

const productSeeds: ProductSeed[] = [
  { name: "Φέτα ΠΟΠ Δωδώνη 400g", category: "Τυριά", unit: "400g", price: 4.99, original: 7.15 },
  { name: "Γραβιέρα Κρήτης 300g", category: "Τυριά", unit: "300g", price: 6.49, original: 8.99 },
  { name: "Γιαούρτι Στραγγιστό 1kg", category: "Γαλακτοκομικά", unit: "1kg", price: 3.29, original: 4.59 },
  { name: "Γάλα Φρέσκο 1L", category: "Γαλακτοκομικά", unit: "1L", price: 1.45 },
  { name: "Κοτόπουλο φιλέτο 1kg", category: "Κρέατα", unit: "1kg", price: 6.99, original: 9.49 },
  { name: "Μοσχαρίσιο κιμάς 500g", category: "Κρέατα", unit: "500g", price: 5.49, original: 7.20 },
  { name: "Σολομός φιλέτο 400g", category: "Ψάρια", unit: "400g", price: 8.99, original: 12.99 },
  { name: "Μπανάνες 1kg", category: "Φρούτα", unit: "1kg", price: 1.79 },
  { name: "Πορτοκάλια 2kg", category: "Φρούτα", unit: "2kg", price: 2.49, original: 3.29 },
  { name: "Ντομάτες σαλάτας 1kg", category: "Λαχανικά", unit: "1kg", price: 2.19 },
  { name: "Πατάτες 2kg", category: "Λαχανικά", unit: "2kg", price: 1.99, original: 2.79 },
  { name: "Νερό 6x1.5L", category: "Ποτά", unit: "6x1.5L", price: 2.49 },
  { name: "Coca-Cola 1.5L", category: "Ποτά", unit: "1.5L", price: 1.59, original: 2.29 },
  { name: "Μπύρα Μύθος 6x500ml", category: "Ποτά", unit: "6x500ml", price: 6.49, original: 8.99 },
  { name: "Απορρυπαντικό πλυντηρίου 3L", category: "Καθαριστικά", unit: "3L", price: 9.99, original: 13.99 },
  { name: "Σαμπουάν 400ml", category: "Καλλυντικά", unit: "400ml", price: 3.49, original: 4.99 },
  { name: "Ελαιόλαδο εξαιρετικά παρθένο 1L", category: "Φρέσκα", unit: "1L", price: 8.99, original: 11.49 },
  { name: "Μέλι θυμαρίσιο 450g", category: "Φρέσκα", unit: "450g", price: 7.99 },
  { name: "Ζυμαρικά Misko 500g", category: "Φρέσκα", unit: "500g", price: 1.29, original: 1.79 },
  { name: "Καφές Loumidis 500g", category: "Φρέσκα", unit: "500g", price: 5.99, original: 7.49 },
];

// ---------------------------------------------------------------------------
// Canonical product comparison
// ---------------------------------------------------------------------------

type CanonicalSeed = {
  id: number;
  manufacturer_brand: string;
  display_name: string;
  size_value: number | null;
  size_unit: string | null;
  pack_count: number;
  variant_descriptor: string | null;
  category: string | null;
  image_url: string | null;
  // brand_slug → { product_name, price, original_price?, url? }
  members: Array<{
    brand_slug: string;
    product_name: string;
    product_url: string | null;
    price: number;
    original_price?: number;
    valid_to?: string;
  }>;
};

const canonicalSeeds: CanonicalSeed[] = [
  {
    id: 101,
    manufacturer_brand: "Coca-Cola",
    display_name: "Coca-Cola Original Taste 1.5L",
    size_value: 1.5,
    size_unit: "l",
    pack_count: 1,
    variant_descriptor: "Original Taste",
    category: "Ποτά",
    image_url: null,
    members: [
      {
        brand_slug: "ab",
        product_name: "Coca-Cola Original Taste 1,5lt",
        product_url: "https://www.ab.gr/p/coca-cola-1-5l",
        price: 1.55,
        original_price: 2.29,
        valid_to: "2026-06-03",
      },
      {
        brand_slug: "sklavenitis",
        product_name: "COCA-COLA Original Taste 1,5lt",
        product_url: "https://www.sklavenitis.gr/p/coca-cola-1-5l",
        price: 1.69,
        original_price: 2.29,
        valid_to: "2026-06-03",
      },
      {
        brand_slug: "mymarket",
        product_name: "Coca-Cola 1,5lt",
        product_url: "https://www.mymarket.gr/p/coca-cola-1-5l",
        price: 1.79,
        valid_to: "2026-06-07",
      },
      {
        brand_slug: "masoutis",
        product_name: "Coca Cola 1,5lt.",
        product_url: "https://www.masoutis.gr/p/coca-cola-1-5l",
        price: 1.75,
        original_price: 2.29,
        valid_to: "2026-06-03",
      },
      {
        brand_slug: "lidl",
        product_name: "Coca-Cola Original 1,5L",
        product_url: "https://www.lidl-hellas.gr/p/coca-cola-1-5l",
        price: 1.59,
        valid_to: "2026-06-10",
      },
    ],
  },
  {
    id: 102,
    manufacturer_brand: "Lacta",
    display_name: "Lacta Γκοφρέτα Φουντούκι 31g",
    size_value: 31,
    size_unit: "g",
    pack_count: 1,
    variant_descriptor: "Φουντούκι",
    category: "Σνακ",
    image_url: null,
    members: [
      {
        brand_slug: "ab",
        product_name: "Lacta Γκοφρέτα Φουντούκι 31g",
        product_url: "https://www.ab.gr/p/lacta-foundouki-31g",
        price: 0.69,
        original_price: 0.85,
        valid_to: "2026-06-03",
      },
      {
        brand_slug: "mymarket",
        product_name: "Lacta Wafer Φουντούκι 31gr",
        product_url: "https://www.mymarket.gr/p/lacta-foundouki-31g",
        price: 0.75,
        valid_to: "2026-06-05",
      },
      {
        brand_slug: "sklavenitis",
        product_name: "LACTA Γκοφρέτα Φουντούκι 31g",
        product_url: "https://www.sklavenitis.gr/p/lacta-foundouki-31g",
        price: 0.79,
        original_price: 0.85,
        valid_to: "2026-06-03",
      },
    ],
  },
  {
    id: 103,
    manufacturer_brand: "Melissa",
    display_name: "Melissa Σπαγγέτι Χωρίς Γλουτένη 400g",
    size_value: 400,
    size_unit: "g",
    pack_count: 1,
    variant_descriptor: "Χωρίς Γλουτένη",
    category: "Ζυμαρικά",
    image_url: null,
    members: [
      {
        brand_slug: "sklavenitis",
        product_name: "MELISSA Σπαγγέτι Χωρίς γλουτένη 400g",
        product_url: "https://www.sklavenitis.gr/p/melissa-gf-400g",
        price: 2.13,
        valid_to: "2026-06-10",
      },
      {
        brand_slug: "mymarket",
        product_name: "Melissa Σπαγγέτι Χωρίς Γλουτένη 400gr",
        product_url: "https://www.mymarket.gr/p/melissa-gf-400g",
        price: 2.29,
        valid_to: "2026-06-15",
      },
    ],
  },
];

function brandBySlug(slug: string): Brand {
  const b = mockBrands.find((br) => br.slug === slug);
  if (!b) {
    throw new Error(`mock brand not found for slug ${slug}`);
  }
  return b;
}

function buildCanonicalOffers(seed: CanonicalSeed): CanonicalOffer[] {
  let nextOfferId = seed.id * 1000;
  let nextProductId = seed.id * 100;
  return seed.members.map((m) => {
    const brand = brandBySlug(m.brand_slug);
    const original = m.original_price ?? null;
    const discount_pct =
      original && original > m.price
        ? Math.round(((original - m.price) / original) * 100)
        : null;
    return {
      brand,
      product: {
        id: nextProductId++,
        name: m.product_name,
        url: m.product_url,
        image_url: null,
      },
      offer: {
        id: nextOfferId++,
        price: m.price,
        original_price: original,
        discount_pct,
        valid_from: "2026-05-25",
        valid_to: m.valid_to ?? null,
        scraped_at: "2026-05-25T08:00:00Z",
      },
    };
  });
}

function summarise(seed: CanonicalSeed): CanonicalProductSummary {
  const offers = buildCanonicalOffers(seed);
  const prices = offers.map((o) => o.offer.price);
  const min_price = Math.min(...prices);
  const max_price = Math.max(...prices);
  const avg_price =
    Math.round((prices.reduce((a, b) => a + b, 0) / prices.length) * 100) / 100;
  const cheapest = offers.reduce((a, b) =>
    a.offer.price <= b.offer.price ? a : b,
  );
  const brands_count = new Set(offers.map((o) => o.brand.slug)).size;
  return {
    id: seed.id,
    canonical_key: `${seed.manufacturer_brand.toLowerCase()}-${seed.id}`,
    manufacturer_brand: seed.manufacturer_brand,
    size_value: seed.size_value,
    size_unit: seed.size_unit,
    pack_count: seed.pack_count,
    variant_descriptor: seed.variant_descriptor,
    display_name: seed.display_name,
    category: seed.category,
    image_url: seed.image_url,
    members_count: offers.length,
    brands_count,
    min_price,
    max_price,
    avg_price,
    cheapest_brand: {
      id: cheapest.brand.id,
      name: cheapest.brand.name,
      slug: cheapest.brand.slug,
    },
  };
}

export const mockCanonicalProducts: CanonicalProductSummary[] =
  canonicalSeeds.map(summarise);

export const mockCanonicalDetails: Record<number, CanonicalProductDetail> =
  Object.fromEntries(
    canonicalSeeds.map((seed) => {
      const summary = summarise(seed);
      const offers = buildCanonicalOffers(seed).sort(
        (a, b) => a.offer.price - b.offer.price,
      );
      const detail: CanonicalProductDetail = {
        ...summary,
        offers,
        price_savings:
          Math.round((summary.max_price - summary.min_price) * 100) / 100,
      };
      return [seed.id, detail];
    }),
  );

// Generate offers across brands. Deterministic so dev reload is stable.
export const mockOffers: Offer[] = (() => {
  const out: Offer[] = [];
  let id = 1;
  const today = new Date("2026-05-25");
  const fmt = (d: Date) => d.toISOString().slice(0, 10);

  for (const brand of mockBrands) {
    for (let i = 0; i < productSeeds.length; i++) {
      const seed = productSeeds[i];
      // Skew prices a little per brand so the UI shows variety.
      const drift = 1 + ((brand.id * 7 + i) % 13) / 100 - 0.06;
      const price = Math.round(seed.price * drift * 100) / 100;
      const original = seed.original
        ? Math.round(seed.original * drift * 100) / 100
        : null;
      const discount_pct =
        original && original > price
          ? Math.round(((original - price) / original) * 100)
          : null;
      const validFrom = new Date(today);
      validFrom.setDate(today.getDate() - ((brand.id + i) % 3));
      const validTo = new Date(today);
      validTo.setDate(today.getDate() + 4 + ((brand.id + i) % 5));
      out.push({
        id: id++,
        price,
        original_price: original,
        discount_pct,
        currency: "EUR",
        valid_from: fmt(validFrom),
        valid_to: fmt(validTo),
        scraped_at: today.toISOString(),
        product: {
          id: id * 10,
          external_id: `${brand.slug}-${i}`,
          name: seed.name,
          url: `${brand.website_url}/product/${i}`,
          image_url: null,
          category: seed.category,
          unit: seed.unit,
        },
        brand,
      });
    }
  }
  return out;
})();
