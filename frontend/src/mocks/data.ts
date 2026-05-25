import type { Brand, Offer } from "@/lib/types";

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
