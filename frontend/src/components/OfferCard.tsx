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
  // "Λήγει σε X ημέρες" — treat ≤3 days as the urgency band.
  const m = validity.match(/Λήγει σε (\d+) ημέρες/);
  if (m && Number(m[1]) <= 3) return true;
  return false;
}

export function OfferCard({ offer, priority = false }: Props) {
  const { product, brand, price, original_price, discount_pct, valid_to, currency } = offer;
  const validity = formatValidity(valid_to);
  const expired = validity === "Έληξε";
  const endingSoon = !expired && isEndingSoon(validity);

  return (
    <Link
      href={`/offers/${offer.id}`}
      prefetch={false}
      className="group flex flex-col overflow-hidden rounded-[var(--radius-soft)] bg-canvas p-3 shadow-raised transition-shadow duration-200 hover:shadow-raised-lg focus:outline-none focus-visible:ring-2 focus-visible:ring-brand"
    >
      <div className="relative aspect-square w-full overflow-hidden rounded-[var(--radius-soft)] bg-canvas shadow-inset">
        {product.image_url ? (
          <Image
            src={product.image_url}
            alt={product.name}
            fill
            sizes="(max-width: 640px) 50vw, (max-width: 1024px) 33vw, 25vw"
            className="object-contain p-3 transition-transform duration-300 group-hover:scale-105"
            priority={priority}
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center text-4xl text-ink-muted/40">
            <span aria-hidden>🛒</span>
          </div>
        )}
        {discount_pct != null && discount_pct > 0 && (
          <span className="absolute left-2 top-2 rounded-full bg-accent px-2.5 py-1 text-xs font-bold uppercase tracking-wide text-white shadow-sm">
            -{discount_pct}%
          </span>
        )}
      </div>

      <div className="flex flex-1 flex-col gap-2 px-1 pt-3">
        <div className="flex items-center justify-between gap-2">
          <BrandChip brand={brand} />
          {product.category && (
            <span className="truncate text-xs text-ink-muted">
              {product.category}
            </span>
          )}
        </div>

        <h3 className="line-clamp-2 min-h-[2.5rem] text-sm font-medium text-ink">
          {product.name}
        </h3>

        {product.unit && (
          <p className="text-xs text-ink-muted">{product.unit}</p>
        )}

        <div className="mt-auto flex items-baseline gap-2">
          <span className="text-xl font-bold text-ink">
            {formatPrice(price, currency)}
          </span>
          {original_price != null && original_price > price && (
            <span className="text-sm text-ink-muted line-through">
              {formatPrice(original_price, currency)}
            </span>
          )}
        </div>

        {validity && (
          <p
            className={
              expired
                ? "text-xs text-ink-muted"
                : endingSoon
                  ? "inline-flex w-fit items-center gap-1 rounded-full bg-warn-soft px-2 py-0.5 text-xs font-medium text-ink-soft"
                  : "text-xs text-ink-soft"
            }
          >
            {validity}
          </p>
        )}
      </div>
    </Link>
  );
}
