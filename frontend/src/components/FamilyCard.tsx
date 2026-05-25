import Image from "next/image";
import Link from "next/link";
import { BrandChip } from "./BrandChip";
import { formatPrice } from "@/lib/format";
import type { FamilySummary } from "@/lib/types";

type Props = {
  family: FamilySummary;
  priority?: boolean;
};

/**
 * Catalogue card for /families. Mirrors the visual hierarchy of
 * CanonicalCard so the catalogue + family list feel like the same
 * surface — image, name, meta row (variants count + cheapest chain),
 * price block. The differentiator is the variants_count badge, which
 * answers the question "how many flavours/scents/shades are on offer".
 */
export function FamilyCard({ family, priority = false }: Props) {
  const {
    key,
    display_name,
    image_url,
    variants_count,
    brands_count,
    min_price,
    max_price,
    cheapest_brand,
    category,
  } = family;

  const savings =
    min_price !== null && max_price !== null
      ? Math.max(0, max_price - min_price)
      : 0;
  const savingsPct =
    max_price !== null && max_price > 0
      ? Math.round((savings / max_price) * 100)
      : 0;

  return (
    <Link
      href={`/families/${encodeURIComponent(key)}`}
      prefetch={false}
      className="group flex flex-col gap-3 overflow-hidden rounded-[var(--radius-soft)] bg-canvas p-3 shadow-raised transition-shadow duration-200 hover:shadow-raised-lg focus:outline-none focus-visible:ring-2 focus-visible:ring-brand"
    >
      <div className="relative aspect-square w-full overflow-hidden rounded-[var(--radius-soft)] bg-canvas shadow-inset">
        {image_url ? (
          <Image
            src={image_url}
            alt={display_name}
            fill
            sizes="(max-width: 640px) 50vw, (max-width: 1024px) 25vw, 16vw"
            className="object-contain p-4 transition-transform duration-300 group-hover:scale-[1.03]"
            priority={priority}
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center text-4xl text-ink-muted/40">
            <span aria-hidden>🛒</span>
          </div>
        )}

        {/* Variants count is the unique value prop of this card. */}
        <span className="absolute left-2 top-2 rounded-full bg-brand-fade px-2.5 py-1 text-[11px] font-bold uppercase tracking-wide text-brand">
          {variants_count} {variants_count === 1 ? "παραλλαγή" : "παραλλαγές"}
        </span>

        {savings > 0 && savingsPct >= 1 && (
          <span className="absolute right-2 top-2 rounded-full bg-accent px-2.5 py-1 text-[11px] font-bold uppercase tracking-wide text-white">
            -{savingsPct}%
          </span>
        )}
      </div>

      <div className="flex flex-1 flex-col gap-1.5 px-1">
        <h3 className="line-clamp-2 min-h-[2.75rem] text-[15px] font-semibold leading-snug text-ink">
          {display_name}
        </h3>

        <p className="text-[11px] font-semibold text-brand">
          {brands_count > 1
            ? `Σε ${brands_count} αλυσίδες`
            : "Σε 1 αλυσίδα"}
        </p>

        <div className="grid min-w-0 grid-cols-2 items-center gap-2 text-[11px] text-ink-muted">
          <div className="min-w-0">
            {cheapest_brand && <BrandChip brand={cheapest_brand} size="dot" />}
          </div>
          {category && (
            <span className="min-w-0 truncate text-right" title={category}>
              {category}
            </span>
          )}
        </div>

        <div className="mt-auto flex items-baseline gap-2 pt-1">
          {min_price !== null ? (
            <>
              <span className="text-xl font-bold text-ink">
                από {formatPrice(min_price)}
              </span>
              {max_price !== null && max_price > min_price && (
                <span className="text-sm text-ink-muted line-through">
                  {formatPrice(max_price)}
                </span>
              )}
            </>
          ) : (
            <span className="text-sm text-ink-muted">
              Χωρίς ενεργές προσφορές
            </span>
          )}
        </div>
      </div>
    </Link>
  );
}
