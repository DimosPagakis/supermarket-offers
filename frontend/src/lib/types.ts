/**
 * Types mirroring the public REST API contract at /api/public/v1/*.
 * Keep these aligned with backend/docs/api.md. The contract is firm —
 * if it diverges, fix the backend.
 */

export type Brand = {
  id: number;
  name: string;
  slug: string;
  website_url: string;
  country_code: string;
};

export type Product = {
  id: number;
  external_id: string | null;
  name: string;
  url: string | null;
  image_url: string | null;
  category: string | null;
  unit: string | null;
  /**
   * Optional pointer to the canonical product this SKU rolls up into. The
   * public OfferResource may not include it yet — treat as best-effort and
   * only render UI when it is non-null.
   */
  canonical_product_id?: number | null;
};

export type Offer = {
  id: number;
  price: number;
  original_price: number | null;
  discount_pct: number | null;
  currency: string;
  valid_from: string | null;
  valid_to: string | null;
  scraped_at: string;
  product: Product;
  brand: Brand;
};

export type PriceHistoryPoint = {
  date: string;
  price: number;
  original_price: number | null;
  discount_pct: number | null;
};

export type OfferWithHistory = Offer & {
  history?: PriceHistoryPoint[];
};

export type PageMeta = {
  current_page: number;
  per_page: number;
  total: number;
  last_page: number;
};

export type PageLinks = {
  first: string;
  last: string;
  next: string | null;
  prev: string | null;
  self: string;
};

export type OffersPage = {
  data: Offer[];
  meta: PageMeta;
  links: PageLinks;
};

export type SortField = "discount_pct" | "price" | "scraped_at";
export type SortDir = "asc" | "desc";

export type OfferQuery = {
  brand?: string[];
  category?: string[];
  min_discount?: number;
  has_discount?: boolean;
  valid_on?: string;
  q?: string;
  sort?: SortField;
  dir?: SortDir;
  page?: number;
  per_page?: number;
};

// ---------------------------------------------------------------------------
// Canonical product comparison
// ---------------------------------------------------------------------------

export type CanonicalCheapestBrand = {
  id: number;
  name: string;
  slug: string;
};

export type CanonicalProductSummary = {
  id: number;
  canonical_key: string;
  manufacturer_brand: string;
  size_value: number | null;
  size_unit: string | null;
  pack_count: number;
  variant_descriptor: string | null;
  display_name: string;
  category: string | null;
  image_url: string | null;
  members_count: number;
  brands_count: number;
  min_price: number;
  max_price: number;
  avg_price: number;
  cheapest_brand: CanonicalCheapestBrand;
};

export type CanonicalOffer = {
  brand: Brand;
  product: {
    id: number;
    name: string;
    url: string | null;
    image_url: string | null;
  };
  offer: {
    id: number;
    price: number;
    original_price: number | null;
    discount_pct: number | null;
    valid_from: string | null;
    valid_to: string | null;
    scraped_at: string;
  };
};

export type CanonicalProductDetail = CanonicalProductSummary & {
  offers: CanonicalOffer[];
  price_savings: number;
};

export type CanonicalProductsPage = {
  data: CanonicalProductSummary[];
  meta: PageMeta;
  links: PageLinks;
};

export type CanonicalSortField =
  | "brands_count"
  | "members_count"
  | "display_name";

export type CanonicalQuery = {
  q?: string;
  brand?: string[];
  category?: string;
  min_brands?: number;
  sort?: CanonicalSortField;
  dir?: SortDir;
  page?: number;
  per_page?: number;
};
