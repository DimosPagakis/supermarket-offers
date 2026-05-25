/**
 * Public API client. All calls hit `${API_BASE}/api/public/v1/*` and use
 * Next's native `fetch` with cache tags so we can revalidate on demand.
 *
 * Server components call these directly. Client components should pass
 * data down via props rather than calling these from the browser — that
 * way we stay under the 120 req/min throttle.
 */

import type {
  Brand,
  Offer,
  OfferQuery,
  OfferWithHistory,
  OffersPage,
} from "./types";
import { isMocksEnabled, mockApi } from "@/mocks/handlers";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8001";

const API_PREFIX = "/api/public/v1";

const OFFERS_TAG = "offers";
const BRANDS_TAG = "brands";
const CATEGORIES_TAG = "categories";

const REVALIDATE_OFFERS = 60 * 5; // 5 min
const REVALIDATE_REFERENCE = 60 * 60; // 1 hour for brands + categories

export function buildOfferQueryString(params: OfferQuery): string {
  const sp = new URLSearchParams();
  if (params.brand?.length) sp.set("brand", params.brand.join(","));
  if (params.category?.length) sp.set("category", params.category.join(","));
  if (typeof params.min_discount === "number")
    sp.set("min_discount", String(params.min_discount));
  if (typeof params.has_discount === "boolean")
    sp.set("has_discount", String(params.has_discount));
  if (params.valid_on) sp.set("valid_on", params.valid_on);
  if (params.q) sp.set("q", params.q);
  if (params.sort) sp.set("sort", params.sort);
  if (params.dir) sp.set("dir", params.dir);
  if (params.page) sp.set("page", String(params.page));
  if (params.per_page) sp.set("per_page", String(params.per_page));
  const s = sp.toString();
  return s ? `?${s}` : "";
}

type FetchOpts = {
  tag: string;
  revalidate: number;
};

async function apiFetch<T>(path: string, opts: FetchOpts): Promise<T> {
  const url = `${API_BASE}${API_PREFIX}${path}`;
  const res = await fetch(url, {
    headers: { Accept: "application/json" },
    next: { revalidate: opts.revalidate, tags: [opts.tag] },
  });
  if (!res.ok) {
    throw new Error(
      `API error ${res.status} ${res.statusText} for ${url}`,
    );
  }
  return (await res.json()) as T;
}

export async function fetchOffers(params: OfferQuery = {}): Promise<OffersPage> {
  if (isMocksEnabled()) return mockApi.offers(params);
  const qs = buildOfferQueryString(params);
  return apiFetch<OffersPage>(`/offers${qs}`, {
    tag: OFFERS_TAG,
    revalidate: REVALIDATE_OFFERS,
  });
}

export async function fetchOffer(
  id: number,
  includeHistory = false,
): Promise<OfferWithHistory> {
  if (isMocksEnabled()) return mockApi.offer(id, includeHistory);
  const qs = includeHistory ? "?include_history=true" : "";
  const json = await apiFetch<{ data: OfferWithHistory }>(
    `/offers/${id}${qs}`,
    { tag: OFFERS_TAG, revalidate: REVALIDATE_OFFERS },
  );
  return json.data;
}

export async function fetchBrands(): Promise<Brand[]> {
  if (isMocksEnabled()) return mockApi.brands();
  const json = await apiFetch<{ data: Brand[] }>("/brands", {
    tag: BRANDS_TAG,
    revalidate: REVALIDATE_REFERENCE,
  });
  return json.data;
}

export async function fetchCategories(): Promise<string[]> {
  if (isMocksEnabled()) return mockApi.categories();
  const json = await apiFetch<{ data: string[] }>("/categories", {
    tag: CATEGORIES_TAG,
    revalidate: REVALIDATE_REFERENCE,
  });
  return json.data;
}

export async function fetchBrandOffers(
  slug: string,
  params: OfferQuery = {},
): Promise<OffersPage> {
  if (isMocksEnabled()) return mockApi.brandOffers(slug, params);
  const qs = buildOfferQueryString(params);
  return apiFetch<OffersPage>(`/brands/${slug}/offers${qs}`, {
    tag: OFFERS_TAG,
    revalidate: REVALIDATE_OFFERS,
  });
}

export async function searchOffers(q: string): Promise<OffersPage> {
  return fetchOffers({ q });
}

// Re-export so callers can keep imports tidy.
export type { Brand, Offer, OfferQuery, OfferWithHistory, OffersPage };
