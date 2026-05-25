/**
 * Translate Next's `searchParams` (string | string[] | undefined) into a
 * typed OfferQuery. The whole app uses URL state as its source of truth
 * so filters are shareable, bookmarkable, and SSR-friendly.
 */

import type {
  CanonicalQuery,
  CanonicalSortField,
  OfferQuery,
  SortDir,
  SortField,
} from "./types";

type Raw = Record<string, string | string[] | undefined>;

function firstString(v: string | string[] | undefined): string | undefined {
  if (Array.isArray(v)) return v[0];
  return v;
}

function csv(v: string | string[] | undefined): string[] | undefined {
  const s = firstString(v);
  if (!s) return undefined;
  const parts = s.split(",").map((x) => x.trim()).filter(Boolean);
  return parts.length ? parts : undefined;
}

export function parseOfferQuery(params: Raw): OfferQuery {
  const out: OfferQuery = {};
  const brand = csv(params.brand);
  if (brand) out.brand = brand;
  const category = csv(params.category);
  if (category) out.category = category;

  const min = firstString(params.min_discount);
  if (min != null && min !== "") {
    const n = Number(min);
    if (Number.isFinite(n) && n >= 0 && n <= 100) out.min_discount = n;
  }

  const hasDiscount = firstString(params.has_discount);
  if (hasDiscount === "true") out.has_discount = true;
  else if (hasDiscount === "false") out.has_discount = false;

  const validOn = firstString(params.valid_on);
  if (validOn) out.valid_on = validOn;

  const q = firstString(params.q);
  if (q) out.q = q;

  const sort = firstString(params.sort);
  if (sort === "discount_pct" || sort === "price" || sort === "scraped_at") {
    out.sort = sort as SortField;
  }
  const dir = firstString(params.dir);
  if (dir === "asc" || dir === "desc") out.dir = dir as SortDir;

  const page = firstString(params.page);
  if (page) {
    const n = Number(page);
    if (Number.isFinite(n) && n > 0) out.page = Math.floor(n);
  }
  const perPage = firstString(params.per_page);
  if (perPage) {
    const n = Number(perPage);
    if (Number.isFinite(n) && n > 0) out.per_page = Math.min(Math.floor(n), 100);
  }
  return out;
}

/**
 * Build a fresh URL search string from an OfferQuery. Used by client
 * components to update the URL when filters change.
 */
export function toSearchString(q: OfferQuery): string {
  const sp = new URLSearchParams();
  if (q.brand?.length) sp.set("brand", q.brand.join(","));
  if (q.category?.length) sp.set("category", q.category.join(","));
  if (typeof q.min_discount === "number") sp.set("min_discount", String(q.min_discount));
  if (typeof q.has_discount === "boolean") sp.set("has_discount", String(q.has_discount));
  if (q.valid_on) sp.set("valid_on", q.valid_on);
  if (q.q) sp.set("q", q.q);
  if (q.sort) sp.set("sort", q.sort);
  if (q.dir) sp.set("dir", q.dir);
  if (q.page && q.page > 1) sp.set("page", String(q.page));
  if (q.per_page) sp.set("per_page", String(q.per_page));
  return sp.toString();
}

// ---------------------------------------------------------------------------
// Canonical product query
// ---------------------------------------------------------------------------

export function parseCanonicalQuery(params: Raw): CanonicalQuery {
  const out: CanonicalQuery = {};

  const q = firstString(params.q);
  if (q) out.q = q;

  const brand = csv(params.brand);
  if (brand) out.brand = brand;

  const category = firstString(params.category);
  if (category) out.category = category;

  const minBrands = firstString(params.min_brands);
  if (minBrands != null && minBrands !== "") {
    const n = Number(minBrands);
    if (Number.isFinite(n) && n >= 1 && n <= 10) out.min_brands = Math.floor(n);
  }

  const sort = firstString(params.sort);
  if (
    sort === "brands_count" ||
    sort === "members_count" ||
    sort === "display_name"
  ) {
    out.sort = sort as CanonicalSortField;
  }
  const dir = firstString(params.dir);
  if (dir === "asc" || dir === "desc") out.dir = dir as SortDir;

  const page = firstString(params.page);
  if (page) {
    const n = Number(page);
    if (Number.isFinite(n) && n > 0) out.page = Math.floor(n);
  }
  const perPage = firstString(params.per_page);
  if (perPage) {
    const n = Number(perPage);
    if (Number.isFinite(n) && n > 0) out.per_page = Math.min(Math.floor(n), 100);
  }
  return out;
}

export function toCanonicalSearchString(q: CanonicalQuery): string {
  const sp = new URLSearchParams();
  if (q.q) sp.set("q", q.q);
  if (q.brand?.length) sp.set("brand", q.brand.join(","));
  if (q.category) sp.set("category", q.category);
  if (typeof q.min_brands === "number")
    sp.set("min_brands", String(q.min_brands));
  if (q.sort) sp.set("sort", q.sort);
  if (q.dir) sp.set("dir", q.dir);
  if (q.page && q.page > 1) sp.set("page", String(q.page));
  if (q.per_page) sp.set("per_page", String(q.per_page));
  return sp.toString();
}
