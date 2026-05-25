import Link from "next/link";
import { brandColour } from "@/lib/brand-colours";
import type { Brand } from "@/lib/types";

type Props = {
  brand: Pick<Brand, "name" | "slug">;
  href?: string;
  size?: "sm" | "md";
};

export function BrandChip({ brand, href, size = "sm" }: Props) {
  const colour = brandColour(brand.slug);
  const padding = size === "sm" ? "px-2 py-0.5 text-xs" : "px-3 py-1 text-sm";
  const chip = (
    <span
      className={`inline-flex items-center rounded-full font-medium ring-1 ring-inset ${padding}`}
      style={{
        backgroundColor: colour.bg,
        color: colour.fg,
        // Subtle ring matches the brand identity hue at low alpha;
        // keeps chips readable against the seasalt canvas.
        boxShadow: `inset 0 0 0 1px ${colour.ring}26`,
      }}
      aria-label={`Αλυσίδα: ${brand.name}`}
    >
      {brand.name}
    </span>
  );
  if (href) {
    return (
      <Link href={href} className="transition-opacity hover:opacity-80">
        {chip}
      </Link>
    );
  }
  return chip;
}
