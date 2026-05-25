/**
 * Brand → accent colour. Slugs match the backend seeder.
 * Used by BrandChip and brand header banners.
 *
 * The visual rework moved chips from "full saturation brand colour"
 * to a *tinted* surface: a soft background derived from the brand's
 * identity hue + a deeper, accessible text colour. Keeps brand
 * recognition without fighting the seasalt canvas.
 *
 *   bg   — soft tint shown as chip background / banner accent strip
 *   fg   — darker brand hue used for text on the tint (≥4.5:1 on bg)
 *   ring — saturated brand hue, used for borders / strong banners
 */

export type BrandColour = {
  bg: string;
  fg: string;
  ring: string;
};

const PALETTE: Record<string, BrandColour> = {
  // AB — red
  ab: { bg: "#FDE4E6", fg: "#9B0512", ring: "#E30613" },
  // Σκλαβενίτης — blue
  sklavenitis: { bg: "#DCEBFA", fg: "#004A83", ring: "#0066B3" },
  // Lidl — yellow + blue
  lidl: { bg: "#FFF4B8", fg: "#0050AA", ring: "#FFD500" },
  // My Market — red
  mymarket: { bg: "#FDE4E7", fg: "#9B0314", ring: "#E40521" },
  // Μασούτης — green
  masoutis: { bg: "#D9F0E2", fg: "#006E34", ring: "#009B48" },
};

const FALLBACK: BrandColour = {
  bg: "#E6F2FB", // brand-fade (Picton tint)
  fg: "#1A4B6E",
  ring: "#5AA9E6",
};

export function brandColour(slug: string): BrandColour {
  return PALETTE[slug] ?? FALLBACK;
}
