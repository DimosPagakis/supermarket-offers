import Link from "next/link";
import { BrandChip } from "./BrandChip";
import { formatDate, formatPrice } from "@/lib/format";
import type { CanonicalOffer } from "@/lib/types";

type Props = {
  offers: CanonicalOffer[];
};

/**
 * Cross-chain price comparison. Each row links to the chain's own product
 * page in a new tab; the brand chip jumps to our brand page; "Λεπτομέρειες"
 * goes to our internal offer detail. The cheapest row is highlighted with
 * a French-pink-tinted background and a ⭐.
 *
 * Renders an empty-state when `offers` is empty (defensive: backend should
 * never return zero, but a stale canonical with no live offers is possible
 * during rebuilds).
 */
export function PriceComparisonTable({ offers }: Props) {
  if (offers.length === 0) {
    return (
      <div
        role="status"
        className="rounded-[var(--radius-soft)] bg-canvas p-6 text-center text-sm text-ink-soft shadow-inset"
      >
        Δεν υπάρχουν ενεργές προσφορές αυτή τη στιγμή για αυτό το προϊόν.
      </div>
    );
  }

  const cheapestPrice = Math.min(...offers.map((o) => o.offer.price));

  return (
    <div className="overflow-hidden rounded-[var(--radius-soft)] bg-canvas shadow-raised">
      <table className="w-full text-sm">
        <thead className="bg-canvas-muted text-left text-xs uppercase tracking-wide text-ink-muted">
          <tr>
            <th scope="col" className="px-4 py-3">
              Αλυσίδα
            </th>
            <th scope="col" className="px-4 py-3 text-right">
              Τιμή
            </th>
            <th scope="col" className="hidden px-4 py-3 text-right sm:table-cell">
              Αρχική
            </th>
            <th scope="col" className="hidden px-4 py-3 text-right sm:table-cell">
              Έκπτωση
            </th>
            <th scope="col" className="hidden px-4 py-3 md:table-cell">
              Έγκυρο έως
            </th>
            <th scope="col" className="px-4 py-3 text-right">
              <span className="sr-only">Σύνδεσμος</span>
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {offers.map((entry) => {
            const { brand, product, offer } = entry;
            const isCheapest = offer.price === cheapestPrice;
            const rowClass = isCheapest
              ? "bg-accent-soft/40"
              : "hover:bg-canvas-muted";
            return (
              <tr key={`${brand.slug}-${offer.id}`} className={rowClass}>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <BrandChip
                      brand={brand}
                      href={`/brand/${brand.slug}`}
                      size="sm"
                    />
                    {isCheapest && (
                      <span
                        aria-label="Φθηνότερη τιμή"
                        title="Φθηνότερη τιμή"
                        className="text-accent"
                      >
                        ⭐
                      </span>
                    )}
                  </div>
                </td>
                <td className="px-4 py-3 text-right font-semibold text-ink">
                  {formatPrice(offer.price)}
                </td>
                <td className="hidden px-4 py-3 text-right text-ink-muted line-through sm:table-cell">
                  {offer.original_price != null
                    ? formatPrice(offer.original_price)
                    : "—"}
                </td>
                <td className="hidden px-4 py-3 text-right sm:table-cell">
                  {(() => {
                    // Same promo-pill precedence as OfferCard: prefer the
                    // brand-supplied `promo_label` over the reconstructed
                    // "-N%" when both are present; fall back to the raw
                    // pct for legacy data; render an em-dash otherwise.
                    const badge = offer.promo_label
                      ? offer.promo_label
                      : offer.discount_pct != null && offer.discount_pct > 0
                        ? `-${offer.discount_pct}%`
                        : null;
                    return badge ? (
                      <span className="rounded-full bg-accent px-2 py-0.5 text-xs font-semibold text-white">
                        {badge}
                      </span>
                    ) : (
                      <span className="text-ink-muted">—</span>
                    );
                  })()}
                </td>
                <td className="hidden px-4 py-3 text-ink-soft md:table-cell">
                  {offer.valid_to ? formatDate(offer.valid_to) : "—"}
                </td>
                <td className="px-4 py-3 text-right">
                  <div className="flex items-center justify-end gap-3">
                    <Link
                      href={`/offers/${offer.id}`}
                      className="text-xs font-medium text-brand transition-colors hover:text-brand-hover"
                    >
                      Λεπτομέρειες
                    </Link>
                    {product.url && (
                      <a
                        href={product.url}
                        target="_blank"
                        rel="noreferrer noopener"
                        className="text-xs font-medium text-ink-soft transition-colors hover:text-brand"
                      >
                        Στο {brand.name} ↗
                      </a>
                    )}
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
