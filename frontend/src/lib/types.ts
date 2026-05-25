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
