import type {
  Brand,
  Offer,
  OfferQuery,
  OfferWithHistory,
  OffersPage,
} from "@/lib/types";
import { mockBrands, mockCategories, mockOffers } from "./data";

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
    // Build a tiny synthetic history.
    const history = Array.from({ length: 8 }).map((_, i) => {
      const d = new Date(found.scraped_at);
      d.setDate(d.getDate() - (7 - i));
      const drift = 1 + (i - 4) * 0.015;
      const price = Math.round(found.price * drift * 100) / 100;
      const original = found.original_price;
      return {
        date: d.toISOString().slice(0, 10),
        price,
        original_price: original,
        discount_pct:
          original && original > price
            ? Math.round(((original - price) / original) * 100)
            : null,
      };
    });
    return Promise.resolve({ ...found, history });
  },
};
