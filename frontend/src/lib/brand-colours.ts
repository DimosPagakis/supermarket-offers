/**
 * Brand → accent colour. Slugs match the backend seeder.
 * Used by BrandChip and brand header banners.
 */

const PALETTE: Record<string, { bg: string; fg: string; ring: string }> = {
  ab: { bg: "#E30613", fg: "#ffffff", ring: "#a30410" },
  sklavenitis: { bg: "#0066B3", fg: "#ffffff", ring: "#004a83" },
  lidl: { bg: "#FFD500", fg: "#0050AA", ring: "#0050AA" },
  mymarket: { bg: "#E40521", fg: "#ffffff", ring: "#a30314" },
  masoutis: { bg: "#009B48", fg: "#ffffff", ring: "#006e34" },
};

const FALLBACK = { bg: "#374151", fg: "#ffffff", ring: "#1f2937" };

export function brandColour(slug: string) {
  return PALETTE[slug] ?? FALLBACK;
}
