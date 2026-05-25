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
 * Catalogue card for /compare. Mirrors OfferCard visually but surfaces the
 * cross-chain story: how many chains carry the product, the price range,
 * and the absolute savings achievable by buying at the cheapest one.
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
      className="group flex flex-col overflow-hidden rounded-xl border border-zinc-200 bg-white shadow-sm transition hover:shadow-md focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 dark:border-zinc-800 dark:bg-zinc-900"
    >
      <div className="relative aspect-square w-full overflow-hidden bg-zinc-100 dark:bg-zinc-800">
        {image_url ? (
          <Image
            src={image_url}
            alt={display_name}
            fill
            sizes="(max-width: 640px) 50vw, (max-width: 1024px) 33vw, 25vw"
            className="object-contain p-3 transition group-hover:scale-105"
            priority={priority}
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center text-4xl text-zinc-300 dark:text-zinc-700">
            <span aria-hidden>🛒</span>
          </div>
        )}
        <span
          className={`absolute left-2 top-2 rounded-md px-2 py-1 text-xs font-bold shadow ${
            everywhere
              ? "bg-amber-500 text-white"
              : "bg-emerald-600 text-white"
          }`}
        >
          {everywhere ? "Σε όλες τις αλυσίδες" : `Σε ${brands_count} αλυσίδες`}
        </span>
      </div>

      <div className="flex flex-1 flex-col gap-2 p-3">
        <h3 className="line-clamp-2 min-h-[2.5rem] text-sm font-medium text-zinc-900 dark:text-zinc-100">
          {display_name}
        </h3>

        <div className="mt-auto flex flex-col gap-1">
          <div className="flex items-baseline gap-2">
            <span className="text-lg font-bold text-emerald-600 dark:text-emerald-400">
              από {formatPrice(min_price)}
            </span>
            <span className="text-sm text-zinc-500">
              έως {formatPrice(max_price)}
            </span>
          </div>
          {savings > 0 && (
            <p className="text-xs font-medium text-rose-600">
              Εξοικονόμηση {formatPrice(savings)}
              {savingsPct > 0 ? ` (${savingsPct}%)` : ""}
            </p>
          )}
          <div className="flex items-center gap-1 pt-1 text-xs text-zinc-500">
            <span>Φθηνότερο:</span>
            <BrandChip brand={cheapest_brand} />
          </div>
        </div>
      </div>
    </Link>
  );
}
