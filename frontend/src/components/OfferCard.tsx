import Image from "next/image";
import Link from "next/link";
import { BrandChip } from "./BrandChip";
import { formatPrice, formatValidity } from "@/lib/format";
import type { Offer } from "@/lib/types";

type Props = {
  offer: Offer;
  priority?: boolean;
};

/** Mirrors the strings produced by formatValidity. */
function isEndingSoon(validity: string): boolean {
  if (!validity) return false;
  if (validity === "Λήγει σήμερα" || validity === "Λήγει αύριο") return true;
  const m = validity.match(/Λήγει σε (\d+) ημέρες/);
  if (m && Number(m[1]) <= 3) return true;
  return false;
}

/**
 * Offer card. Hierarchy:
 *   1. Image (largest visual)
 *   2. Discount pill (signal, top-right of image)
 *   3. Name (2 lines, generous leading)
 *   4. Meta line (brand dot + category, both small, secondary colour)
 *   5. Price block (sale price big, original strikethrough small)
 *   6. Validity (only when urgent / expired)
 *
 * Brand is intentionally a small coloured dot + text — not a big pill —
 * so it doesn't fight the product name for attention. Category sits on
 * the same line, separated by · and ellipsis-truncated at row level.
 */
export function OfferCard({ offer, priority = false }: Props) {
  const { product, brand, price, original_price, discount_pct, valid_to, currency } = offer;
  const validity = formatValidity(valid_to);
  const expired = validity === "Έληξε";
  const endingSoon = !expired && isEndingSoon(validity);

  return (
    <Link
      href={`/offers/${offer.id}`}
      prefetch={false}
      className="group flex flex-col gap-3 overflow-hidden rounded-[var(--radius-soft)] bg-canvas p-3 shadow-raised transition-shadow duration-200 hover:shadow-raised-lg focus:outline-none focus-visible:ring-2 focus-visible:ring-brand"
    >
      <div className="relative aspect-square w-full overflow-hidden rounded-[var(--radius-soft)] bg-canvas shadow-inset">
        {product.image_url ? (
          <Image
            src={product.image_url}
            alt={product.name}
            fill
            sizes="(max-width: 640px) 50vw, (max-width: 1024px) 33vw, 25vw"
            className="object-contain p-4 transition-transform duration-300 group-hover:scale-105"
            priority={priority}
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center text-4xl text-ink-muted/40">
            <span aria-hidden>🛒</span>
          </div>
        )}
        {discount_pct != null && discount_pct > 0 && (
          <span className="absolute right-2 top-2 rounded-full bg-accent px-2.5 py-1 text-[11px] font-bold uppercase tracking-wide text-white">
            -{discount_pct}%
          </span>
        )}
      </div>

      <div className="flex flex-1 flex-col gap-2 px-1">
        {/* Title gets prime real estate — base size, two lines max with
            comfortable leading so Greek diacritics breathe. */}
        <h3 className="line-clamp-2 min-h-[2.75rem] text-[15px] font-semibold leading-snug text-ink">
          {product.name}
        </h3>

        {/* Meta line: brand dot + category. Single row, ellipsis on
            overflow so we never get a wrapped two-line brand pill again. */}
        <div className="flex min-w-0 items-center gap-2 text-[11px] text-ink-muted">
          <BrandChip brand={brand} size="dot" />
          {product.category && (
            <>
              <span aria-hidden className="text-ink-muted/50">·</span>
              <span className="truncate" title={product.category}>
                {product.category}
              </span>
            </>
          )}
          {product.unit && (
            <>
              <span aria-hidden className="text-ink-muted/50">·</span>
              <span className="shrink-0">{product.unit}</span>
            </>
          )}
        </div>

        {/* Price block always at the bottom — sale price prominent, original
            beside it as strikethrough so the discount story reads at a glance. */}
        <div className="mt-auto flex items-baseline gap-2 pt-1">
          <span className="text-xl font-bold text-ink">
            {formatPrice(price, currency)}
          </span>
          {original_price != null && original_price > price && (
            <span className="text-sm text-ink-muted line-through">
              {formatPrice(original_price, currency)}
            </span>
          )}
        </div>

        {/* Validity. Only render when it carries information: urgent
            (≤3 days), expired, or absent. The "ends in X days" copy is
            noise when X is, say, 28. */}
        {validity && (expired || endingSoon) && (
          <p
            className={
              expired
                ? "text-[11px] text-ink-muted"
                : "inline-flex w-fit items-center gap-1 rounded-full bg-warn-soft px-2 py-0.5 text-[11px] font-medium text-ink-soft"
            }
          >
            {validity}
          </p>
        )}
      </div>
    </Link>
  );
}
