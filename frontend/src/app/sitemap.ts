import type { MetadataRoute } from "next";
import { fetchBrands, fetchCanonicalProducts } from "@/lib/api";

const SITE_URL =
  process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";

const CANONICAL_SITEMAP_CAP = 500;

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const now = new Date();
  const staticUrls: MetadataRoute.Sitemap = [
    { url: `${SITE_URL}/`, lastModified: now, changeFrequency: "daily", priority: 1 },
    { url: `${SITE_URL}/offers`, lastModified: now, changeFrequency: "daily", priority: 0.9 },
    { url: `${SITE_URL}/compare`, lastModified: now, changeFrequency: "daily", priority: 0.9 },
    { url: `${SITE_URL}/about`, lastModified: now, changeFrequency: "monthly", priority: 0.3 },
  ];

  let brands: { slug: string }[] = [];
  try {
    brands = await fetchBrands();
  } catch {
    // Backend down at build time? Fall back to just the static pages so
    // builds aren't blocked on the API being up.
    brands = [];
  }

  const brandUrls: MetadataRoute.Sitemap = brands.map((b) => ({
    url: `${SITE_URL}/brand/${b.slug}`,
    lastModified: now,
    changeFrequency: "daily",
    priority: 0.7,
  }));

  // Lazy-fetch canonical products at build time. Cap to keep the build
  // bounded — the long tail of single-chain canonicals isn't valuable for
  // SEO anyway.
  let canonicals: { id: number }[] = [];
  try {
    const page = await fetchCanonicalProducts({
      per_page: Math.min(CANONICAL_SITEMAP_CAP, 100),
      min_brands: 2,
    });
    canonicals = page.data.slice(0, CANONICAL_SITEMAP_CAP);
  } catch {
    canonicals = [];
  }

  const canonicalUrls: MetadataRoute.Sitemap = canonicals.map((c) => ({
    url: `${SITE_URL}/compare/${c.id}`,
    lastModified: now,
    changeFrequency: "daily",
    priority: 0.8,
  }));

  return [...staticUrls, ...brandUrls, ...canonicalUrls];
}
