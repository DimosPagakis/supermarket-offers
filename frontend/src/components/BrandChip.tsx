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
      className={`inline-flex items-center rounded-[var(--radius-soft-pill)] font-medium shadow-raised-sm ${padding}`}
      style={{
        backgroundColor: colour.bg,
        color: colour.fg,
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
