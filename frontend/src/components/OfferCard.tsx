import Image from "next/image";
import Link from "next/link";
import { BrandChip } from "./BrandChip";
import { formatPrice, formatValidity } from "@/lib/format";
import type { Offer } from "@/lib/types";

type Props = {
  offer: Offer;
  priority?: boolean;
};

export function OfferCard({ offer, priority = false }: Props) {
  const { product, brand, price, original_price, discount_pct, valid_to, currency } = offer;
  const validity = formatValidity(valid_to);
  const expired = validity === "Έληξε";

  return (
    <Link
      href={`/offers/${offer.id}`}
      prefetch={false}
      className="group flex flex-col overflow-hidden rounded-xl border border-zinc-200 bg-white shadow-sm transition hover:shadow-md focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 dark:border-zinc-800 dark:bg-zinc-900"
    >
      <div className="relative aspect-square w-full overflow-hidden bg-zinc-100 dark:bg-zinc-800">
        {product.image_url ? (
          <Image
            src={product.image_url}
            alt={product.name}
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
        {discount_pct != null && discount_pct > 0 && (
          <span className="absolute left-2 top-2 rounded-md bg-rose-600 px-2 py-1 text-xs font-bold text-white shadow">
            -{discount_pct}%
          </span>
        )}
      </div>

      <div className="flex flex-1 flex-col gap-2 p-3">
        <div className="flex items-center justify-between gap-2">
          <BrandChip brand={brand} />
          {product.category && (
            <span className="truncate text-xs text-zinc-500 dark:text-zinc-400">
              {product.category}
            </span>
          )}
        </div>

        <h3 className="line-clamp-2 min-h-[2.5rem] text-sm font-medium text-zinc-900 dark:text-zinc-100">
          {product.name}
        </h3>

        {product.unit && (
          <p className="text-xs text-zinc-500 dark:text-zinc-400">{product.unit}</p>
        )}

        <div className="mt-auto flex items-baseline gap-2">
          <span className="text-xl font-bold text-emerald-600 dark:text-emerald-400">
            {formatPrice(price, currency)}
          </span>
          {original_price != null && original_price > price && (
            <span className="text-sm text-zinc-400 line-through">
              {formatPrice(original_price, currency)}
            </span>
          )}
        </div>

        {validity && (
          <p
            className={`text-xs ${expired ? "text-zinc-400" : "text-zinc-600 dark:text-zinc-400"}`}
          >
            {validity}
          </p>
        )}
      </div>
    </Link>
  );
}
