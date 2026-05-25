import Image from "next/image";
import Link from "next/link";
import { BrandChip } from "./BrandChip";
import { formatPrice } from "@/lib/format";
import type { CanonicalProductSummary } from "@/lib/types";

type Props = {
  product: CanonicalProductSummary;
  priority?: boolean;
};

/**
 * Catalogue card for /compare. Light, neumorphic, deliberately minimal —
 * one prominent price, one savings badge, one cheapest-chain chip. The
 * brand-count badge sits as a subtle overlay on the image; everything
 * else lives in a clean two-line caption.
 */
export function CanonicalCard({ product, priority = false }: Props) {
  const {
    id,
    display_name,
    image_url,
    brands_count,
    min_price,
    max_price,
    cheapest_brand,
  } = product;

  const savings = Math.max(0, max_price - min_price);
  const savingsPct =
    max_price > 0 ? Math.round((savings / max_price) * 100) : 0;
  const everywhere = brands_count >= 5;

  return (
    <Link
      href={`/compare/${id}`}
      prefetch={false}
      className="group bg-canvas shadow-raised hover:shadow-raised-lg rounded-[var(--radius-soft)] p-3 flex flex-col gap-3 transition-shadow focus:outline-none focus-visible:ring-2 focus-visible:ring-brand"
    >
      <div className="relative aspect-square w-full overflow-hidden rounded-[var(--radius-soft)] shadow-inset bg-canvas">
        {image_url ? (
          <Image
            src={image_url}
            alt={display_name}
            fill
            sizes="(max-width: 640px) 50vw, (max-width: 1024px) 25vw, 16vw"
            className="object-contain p-4 transition group-hover:scale-[1.03]"
            priority={priority}
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center text-4xl text-ink-muted">
            <span aria-hidden>🛒</span>
          </div>
        )}

        {/* Brand-count chip — subtle, top-left, brand-fade pill */}
        <span
          className={`absolute left-2 top-2 rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${
            everywhere
              ? "bg-warn-soft text-ink"
              : "bg-brand-fade text-brand"
          }`}
        >
          {everywhere ? `Σε ${brands_count} αλυσίδες · παντού` : `Σε ${brands_count} αλυσίδες`}
        </span>

        {/* Savings chip — top-right, French pink, only when there's a real saving */}
        {savings > 0 && savingsPct >= 1 && (
          <span className="absolute right-2 top-2 rounded-full bg-accent px-2.5 py-0.5 text-[11px] font-bold text-white">
            -{savingsPct}%
          </span>
        )}
      </div>

      <div className="flex flex-col gap-2 px-1">
        <h3 className="line-clamp-2 min-h-[2.5rem] text-sm font-medium text-ink">
          {display_name}
        </h3>

        <div className="flex items-baseline gap-2">
          <span className="text-lg font-bold text-ink">
            από {formatPrice(min_price)}
          </span>
          {max_price > min_price && (
            <span className="text-xs text-ink-muted line-through">
              {formatPrice(max_price)}
            </span>
          )}
        </div>

        {cheapest_brand && (
          <div className="flex items-center gap-2 text-[11px] text-ink-muted">
            <span>φθηνότερο σε</span>
            <BrandChip brand={cheapest_brand} />
          </div>
        )}
      </div>
    </Link>
  );
}
