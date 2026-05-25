import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { notFound } from "next/navigation";
import { BrandChip } from "@/components/BrandChip";
import { PriceHistoryChart } from "@/components/PriceHistoryChart";
import { fetchOffer } from "@/lib/api";
import { formatDate, formatPrice, formatValidity } from "@/lib/format";

async function loadOffer(idRaw: string) {
  const id = Number(idRaw);
  if (!Number.isFinite(id) || id <= 0) return null;
  try {
    return await fetchOffer(id, true);
  } catch {
    return null;
  }
}

export async function generateMetadata(
  { params }: PageProps<"/offers/[id]">,
): Promise<Metadata> {
  const { id } = await params;
  const offer = await loadOffer(id);
  if (!offer) return { title: "Προσφορά" };
  const title = `${offer.product.name} — ${formatPrice(offer.price, offer.currency)}`;
  return {
    title,
    description: `Προσφορά από ${offer.brand.name}. ${offer.product.unit ?? ""}`.trim(),
    openGraph: {
      title,
      description: `${offer.brand.name} · ${formatPrice(offer.price, offer.currency)}`,
      images: offer.product.image_url ? [{ url: offer.product.image_url }] : undefined,
      type: "website",
    },
  };
}

export default async function OfferDetailPage({
  params,
}: PageProps<"/offers/[id]">) {
  const { id } = await params;
  const offer = await loadOffer(id);
  if (!offer) notFound();

  const { product, brand, price, original_price, discount_pct, currency, valid_from, valid_to, history } = offer;
  const savings =
    original_price != null && original_price > price ? original_price - price : null;

  return (
    <article className="flex flex-col gap-6">
      <nav className="text-sm text-zinc-500">
        <Link href="/offers" className="hover:text-emerald-600">
          ← Όλες οι προσφορές
        </Link>
      </nav>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        <div className="relative aspect-square overflow-hidden rounded-xl border border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-900">
          {product.image_url ? (
            <Image
              src={product.image_url}
              alt={product.name}
              fill
              sizes="(max-width: 768px) 100vw, 50vw"
              className="object-contain p-6"
              priority
            />
          ) : (
            <div className="flex h-full w-full items-center justify-center text-7xl text-zinc-300 dark:text-zinc-700">
              <span aria-hidden>🛒</span>
            </div>
          )}
          {discount_pct != null && discount_pct > 0 && (
            <span className="absolute left-3 top-3 rounded-md bg-rose-600 px-3 py-1 text-sm font-bold text-white shadow">
              -{discount_pct}%
            </span>
          )}
        </div>

        <div className="flex flex-col gap-4">
          <BrandChip
            brand={brand}
            href={`/brand/${brand.slug}`}
            size="md"
          />
          <h1 className="text-2xl font-bold tracking-tight">{product.name}</h1>
          {product.category && (
            <p className="text-sm text-zinc-500">{product.category}</p>
          )}
          {product.unit && (
            <p className="text-sm text-zinc-600 dark:text-zinc-400">
              Συσκευασία: {product.unit}
            </p>
          )}

          <div className="flex items-baseline gap-3">
            <span className="text-4xl font-bold text-emerald-600 dark:text-emerald-400">
              {formatPrice(price, currency)}
            </span>
            {original_price != null && original_price > price && (
              <span className="text-xl text-zinc-400 line-through">
                {formatPrice(original_price, currency)}
              </span>
            )}
          </div>
          {savings != null && (
            <p className="text-sm font-medium text-rose-600">
              Εξοικονομείς {formatPrice(savings, currency)}
            </p>
          )}

          <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
            {valid_from && (
              <>
                <dt className="text-zinc-500">Ισχύς από</dt>
                <dd>{formatDate(valid_from)}</dd>
              </>
            )}
            {valid_to && (
              <>
                <dt className="text-zinc-500">Ισχύς έως</dt>
                <dd>
                  {formatDate(valid_to)}{" "}
                  <span className="text-xs text-zinc-500">
                    ({formatValidity(valid_to)})
                  </span>
                </dd>
              </>
            )}
          </dl>

          {product.url && (
            <a
              href={product.url}
              target="_blank"
              rel="noreferrer noopener"
              className="mt-2 inline-flex items-center justify-center rounded-md bg-emerald-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-emerald-500"
            >
              Δες στο {brand.name} ↗
            </a>
          )}

          {product.canonical_product_id != null && (
            <Link
              href={`/compare/${product.canonical_product_id}`}
              className="inline-flex items-center justify-center rounded-md border border-emerald-600 bg-white px-4 py-2 text-sm font-semibold text-emerald-700 transition hover:bg-emerald-50 dark:bg-zinc-900 dark:text-emerald-400 dark:hover:bg-zinc-800"
            >
              Σύγκριση σε άλλες αλυσίδες →
            </Link>
          )}
        </div>
      </div>

      {history && history.length > 1 && (
        <PriceHistoryChart history={history} currency={currency} />
      )}
    </article>
  );
}
