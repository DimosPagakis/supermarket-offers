import Link from "next/link";
import { brandColour } from "@/lib/brand-colours";
import type { Brand } from "@/lib/types";

type Props = {
  brand: Pick<Brand, "name" | "slug">;
  href?: string;
  /**
   * `sm` — table cells, hero header, comparison rows. Full pill.
   * `md` — larger contexts (brand banner). Full pill.
   * `dot` — card meta row. A coloured dot + the brand name in
   *         secondary text. Tiny, doesn't compete with the product
   *         name for visual weight.
   */
  size?: "sm" | "md" | "dot";
};

export function BrandChip({ brand, href, size = "sm" }: Props) {
  const colour = brandColour(brand.slug);

  if (size === "dot") {
    const dot = (
      <span
        className="inline-flex items-center gap-1.5 min-w-0 text-[11px] font-medium text-ink-soft"
        aria-label={`Αλυσίδα: ${brand.name}`}
      >
        <span
          className="inline-block h-2 w-2 shrink-0 rounded-full"
          style={{ backgroundColor: colour.bg }}
          aria-hidden
        />
        <span className="truncate">{brand.name}</span>
      </span>
    );
    if (href) {
      return (
        <Link href={href} className="min-w-0 transition-opacity hover:opacity-80">
          {dot}
        </Link>
      );
    }
    return dot;
  }

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
