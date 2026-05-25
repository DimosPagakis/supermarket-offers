import type {
  Brand,
  CanonicalProductDetail,
  CanonicalProductSummary,
  CanonicalProductsPage,
  CanonicalQuery,
  FamiliesPage,
  FamilyDetail,
  FamilyQuery,
  FamilySummary,
  Offer,
  OfferQuery,
  OfferWithHistory,
  OffersPage,
} from "@/lib/types";
import {
  mockBrands,
  mockCanonicalDetails,
  mockCanonicalProducts,
  mockCategories,
  mockFamilies,
  mockFamilyDetails,
  mockOffers,
} from "./data";

export function isMocksEnabled(): boolean {
  return process.env.NEXT_PUBLIC_USE_MOCKS === "true";
}

function applyFilters(offers: Offer[], q: OfferQuery): Offer[] {
  let list = offers;
  if (q.brand?.length) {
    const set = new Set(q.brand);
    list = list.filter((o) => set.has(o.brand.slug));
  }
  if (q.category?.length) {
    const set = new Set(q.category);
    list = list.filter((o) => o.product.category && set.has(o.product.category));
  }
  if (typeof q.min_discount === "number" && q.min_discount > 0) {
    list = list.filter((o) => (o.discount_pct ?? 0) >= q.min_discount!);
  }
  if (q.has_discount) {
    list = list.filter((o) => o.discount_pct != null && o.discount_pct > 0);
  }
  if (q.q) {
    const needle = q.q.toLowerCase();
    list = list.filter((o) => o.product.name.toLowerCase().includes(needle));
  }
  if (q.valid_on) {
    list = list.filter((o) => {
      if (!o.valid_from || !o.valid_to) return true;
      return q.valid_on! >= o.valid_from && q.valid_on! <= o.valid_to;
    });
  }
  const sort = q.sort ?? "discount_pct";
  const dir = q.dir ?? "desc";
  const mult = dir === "asc" ? 1 : -1;
  list = [...list].sort((a, b) => {
    const av = (a[sort as keyof Offer] as number | null) ?? -Infinity;
    const bv = (b[sort as keyof Offer] as number | null) ?? -Infinity;
    if (av === bv) return 0;
    return av > bv ? mult : -mult;
  });
  return list;
}

function paginate(list: Offer[], q: OfferQuery): OffersPage {
  const per_page = Math.min(q.per_page ?? 50, 100);
  const page = q.page ?? 1;
  const total = list.length;
  const last_page = Math.max(1, Math.ceil(total / per_page));
  const start = (page - 1) * per_page;
  const data = list.slice(start, start + per_page);
  const base = "/api/public/v1/offers";
  const link = (p: number | null) =>
    p == null ? null : `${base}?page=${p}&per_page=${per_page}`;
  return {
    data,
    meta: { current_page: page, per_page, total, last_page },
    links: {
      first: link(1)!,
      last: link(last_page)!,
      next: page < last_page ? link(page + 1) : null,
      prev: page > 1 ? link(page - 1) : null,
      self: link(page)!,
    },
  };
}

export const mockApi = {
  brands(): Promise<Brand[]> {
    return Promise.resolve(mockBrands);
  },
  categories(): Promise<string[]> {
    return Promise.resolve(mockCategories);
  },
  offers(q: OfferQuery = {}): Promise<OffersPage> {
    return Promise.resolve(paginate(applyFilters(mockOffers, q), q));
  },
  brandOffers(slug: string, q: OfferQuery = {}): Promise<OffersPage> {
    const filtered = mockOffers.filter((o) => o.brand.slug === slug);
    return Promise.resolve(paginate(applyFilters(filtered, q), q));
  },
  offer(id: number, includeHistory = false): Promise<OfferWithHistory> {
    const found = mockOffers.find((o) => o.id === id);
    if (!found) return Promise.reject(new Error(`offer ${id} not found`));
    if (!includeHistory) return Promise.resolve(found);
    // Build a tiny synthetic history. Shape mirrors the real
    // `/api/public/v1/offers/{id}?include_history=true` response so
    // callers see the same fields whether mocks are on or off.
    const history = Array.from({ length: 8 }).map((_, i) => {
      const d = new Date(found.scraped_at);
      d.setDate(d.getDate() - (7 - i));
      const drift = 1 + (i - 4) * 0.015;
      const price = Math.round(found.price * drift * 100) / 100;
      const original = found.original_price;
      return {
        id: found.id * 1000 + i,
        price,
        original_price: original,
        discount_pct:
          original && original > price
            ? Math.round(((original - price) / original) * 100)
            : null,
        promo_label: found.promo_label ?? null,
        promo_type: found.promo_type ?? null,
        currency: found.currency,
        scraped_at: d.toISOString(),
      };
    });
    return Promise.resolve({ ...found, history });
  },
  canonicalProducts(q: CanonicalQuery = {}): Promise<CanonicalProductsPage> {
    return Promise.resolve(
      paginateCanonical(applyCanonicalFilters(mockCanonicalProducts, q), q),
    );
  },
  canonicalProduct(id: number): Promise<CanonicalProductDetail> {
    const found = mockCanonicalDetails[id];
    if (!found) {
      return Promise.reject(new Error(`canonical product ${id} not found`));
    }
    return Promise.resolve(found);
  },
  families(q: FamilyQuery = {}): Promise<FamiliesPage> {
    return Promise.resolve(paginateFamilies(applyFamilyFilters(mockFamilies, q), q));
  },
  family(key: string): Promise<FamilyDetail> {
    const found = mockFamilyDetails[key];
    if (!found) {
      return Promise.reject(new Error(`family ${key} not found`));
    }
    return Promise.resolve(found);
  },
};

// ---------------------------------------------------------------------------
// Canonical product mock helpers
// ---------------------------------------------------------------------------

function applyCanonicalFilters(
  items: CanonicalProductSummary[],
  q: CanonicalQuery,
): CanonicalProductSummary[] {
  let list = items;
  if (q.q) {
    const needle = q.q.toLowerCase();
    list = list.filter((c) => c.display_name.toLowerCase().includes(needle));
  }
  if (q.brand?.length) {
    const set = new Set(q.brand);
    // Canonical summaries only carry the cheapest brand, so we filter on
    // mock canonical details to honour "any member in those brands".
    list = list.filter((c) => {
      const detail = mockCanonicalDetails[c.id];
      if (!detail) return c.cheapest_brand ? set.has(c.cheapest_brand.slug) : false;
      return detail.offers.some((o) => set.has(o.brand.slug));
    });
  }
  if (q.category) {
    list = list.filter((c) => c.category === q.category);
  }
  const minBrands = q.min_brands ?? 2;
  list = list.filter((c) => c.brands_count >= minBrands);

  const sort = q.sort ?? "brands_count";
  const dir = q.dir ?? (sort === "display_name" ? "asc" : "desc");
  const mult = dir === "asc" ? 1 : -1;
  list = [...list].sort((a, b) => {
    if (sort === "display_name") {
      return a.display_name.localeCompare(b.display_name, "el") * mult;
    }
    const av = a[sort];
    const bv = b[sort];
    if (av === bv) return 0;
    return av > bv ? mult : -mult;
  });
  return list;
}

function paginateCanonical(
  list: CanonicalProductSummary[],
  q: CanonicalQuery,
): CanonicalProductsPage {
  const per_page = Math.min(q.per_page ?? 24, 100);
  const page = q.page ?? 1;
  const total = list.length;
  const last_page = Math.max(1, Math.ceil(total / per_page));
  const start = (page - 1) * per_page;
  const data = list.slice(start, start + per_page);
  const base = "/api/public/v1/canonical-products";
  const link = (p: number | null) =>
    p == null ? null : `${base}?page=${p}&per_page=${per_page}`;
  return {
    data,
    meta: { current_page: page, per_page, total, last_page },
    links: {
      first: link(1)!,
      last: link(last_page)!,
      next: page < last_page ? link(page + 1) : null,
      prev: page > 1 ? link(page - 1) : null,
      self: link(page)!,
    },
  };
}

// ---------------------------------------------------------------------------
// Family mock helpers — semantics mirror the backend
// FamilyController#index: filter, sort by aggregate or price, paginate.
// ---------------------------------------------------------------------------

function applyFamilyFilters(
  items: FamilySummary[],
  q: FamilyQuery,
): FamilySummary[] {
  let list = items;
  if (q.q) {
    const needle = q.q.toLowerCase();
    list = list.filter((f) => f.display_name.toLowerCase().includes(needle));
  }
  if (q.manufacturer) {
    const needle = q.manufacturer.toLowerCase();
    list = list.filter((f) => f.manufacturer_brand.toLowerCase() === needle);
  }
  if (q.category) {
    list = list.filter((f) => f.category === q.category);
  }
  if (q.brand?.length) {
    const set = new Set(q.brand);
    list = list.filter((f) => {
      const detail = mockFamilyDetails[f.key];
      if (!detail) {
        return f.cheapest_brand ? set.has(f.cheapest_brand.slug) : false;
      }
      return detail.variants.some((v) =>
        v.products.some((p) => set.has(p.brand.slug)),
      );
    });
  }
  const minVariants = q.min_variants ?? 2;
  list = list.filter((f) => f.variants_count >= minVariants);
  const minBrands = q.min_brands ?? 1;
  list = list.filter((f) => f.brands_count >= minBrands);

  const sort = q.sort ?? "variants_count";
  const dir = q.dir ?? "desc";
  const mult = dir === "asc" ? 1 : -1;
  list = [...list].sort((a, b) => {
    const av =
      sort === "min_price"
        ? a.min_price ?? Infinity
        : sort === "avg_price"
          ? a.avg_price ?? Infinity
          : sort === "brands_count"
            ? a.brands_count
            : a.variants_count;
    const bv =
      sort === "min_price"
        ? b.min_price ?? Infinity
        : sort === "avg_price"
          ? b.avg_price ?? Infinity
          : sort === "brands_count"
            ? b.brands_count
            : b.variants_count;
    if (av === bv) return 0;
    return av > bv ? mult : -mult;
  });
  return list;
}

function paginateFamilies(
  list: FamilySummary[],
  q: FamilyQuery,
): FamiliesPage {
  const per_page = Math.min(q.per_page ?? 24, 100);
  const page = q.page ?? 1;
  const total = list.length;
  const last_page = Math.max(1, Math.ceil(total / per_page));
  const start = (page - 1) * per_page;
  const data = list.slice(start, start + per_page);
  const base = "/api/public/v1/families";
  const link = (p: number | null) =>
    p == null ? null : `${base}?page=${p}&per_page=${per_page}`;
  return {
    data,
    meta: { current_page: page, per_page, total, last_page },
    links: {
      first: link(1)!,
      last: link(last_page)!,
      next: page < last_page ? link(page + 1) : null,
      prev: page > 1 ? link(page - 1) : null,
      self: link(page)!,
    },
  };
}
