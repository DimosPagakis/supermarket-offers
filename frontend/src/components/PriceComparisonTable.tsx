import Link from "next/link";
import { BrandChip } from "./BrandChip";
import { formatDate, formatPrice } from "@/lib/format";
import type { CanonicalOffer } from "@/lib/types";

type Props = {
  offers: CanonicalOffer[];
};

/**
 * Cross-chain price comparison. Each row links to the chain's own product
 * page in a new tab; clicking the brand chip jumps to our brand page; the
 * "↗ Δες προσφορά" link goes to our internal offer detail. The cheapest
 * row is highlighted with a ⭐.
 *
 * Renders an empty-state when `offers` is empty (defensive: backend should
 * never return zero, but a stale canonical with no live offers is
 * possible during rebuilds).
 */
export function PriceComparisonTable({ offers }: Props) {
  if (offers.length === 0) {
    return (
      <div
        role="status"
        className="rounded-xl border border-dashed border-zinc-300 bg-white p-6 text-center text-sm text-zinc-600 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-400"
      >
        Δεν υπάρχουν ενεργές προσφορές αυτή τη στιγμή για αυτό το προϊόν.
      </div>
    );
  }

  const cheapestPrice = Math.min(...offers.map((o) => o.offer.price));

  return (
    <div className="overflow-hidden rounded-xl border border-zinc-200 bg-white shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
      <table className="w-full text-sm">
        <thead className="bg-zinc-50 text-left text-xs uppercase tracking-wide text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400">
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
        <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800">
          {offers.map((entry) => {
            const { brand, product, offer } = entry;
            const isCheapest = offer.price === cheapestPrice;
            const rowClass = isCheapest
              ? "bg-emerald-50/80 dark:bg-emerald-900/20"
              : "hover:bg-zinc-50 dark:hover:bg-zinc-800/50";
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
                        className="text-amber-500"
                      >
                        ⭐
                      </span>
                    )}
                  </div>
                </td>
                <td className="px-4 py-3 text-right font-semibold text-zinc-900 dark:text-zinc-100">
                  {formatPrice(offer.price)}
                </td>
                <td className="hidden px-4 py-3 text-right text-zinc-400 line-through sm:table-cell">
                  {offer.original_price != null
                    ? formatPrice(offer.original_price)
                    : "—"}
                </td>
                <td className="hidden px-4 py-3 text-right sm:table-cell">
                  {offer.discount_pct != null && offer.discount_pct > 0 ? (
                    <span className="rounded-md bg-rose-100 px-2 py-0.5 text-xs font-semibold text-rose-700 dark:bg-rose-900/30 dark:text-rose-300">
                      -{offer.discount_pct}%
                    </span>
                  ) : (
                    <span className="text-zinc-400">—</span>
                  )}
                </td>
                <td className="hidden px-4 py-3 text-zinc-600 dark:text-zinc-400 md:table-cell">
                  {offer.valid_to ? formatDate(offer.valid_to) : "—"}
                </td>
                <td className="px-4 py-3 text-right">
                  <div className="flex items-center justify-end gap-3">
                    <Link
                      href={`/offers/${offer.id}`}
                      className="text-xs font-medium text-emerald-700 hover:underline dark:text-emerald-400"
                    >
                      Λεπτομέρειες
                    </Link>
                    {product.url && (
                      <a
                        href={product.url}
                        target="_blank"
                        rel="noreferrer noopener"
                        className="text-xs font-medium text-zinc-600 hover:text-emerald-600 dark:text-zinc-400"
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
