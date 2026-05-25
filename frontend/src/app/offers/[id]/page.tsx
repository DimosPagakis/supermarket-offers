import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import { BrandChip } from "@/components/BrandChip";
import { PriceHistoryChart } from "@/components/PriceHistoryChart";
import { fetchOffer } from "@/lib/api";
import { formatDate, formatPrice, formatValidity } from "@/lib/format";

/**
 * Find the most-recent offer id for this product, if it differs from the
 * one in the URL. The crawler inserts a fresh offer row per run; old rows
 * persist for price-history. A bookmarked / search-engine-cached URL like
 * `/offers/7787` can therefore land on a stale snapshot whose pricing or
 * promo-label predates a later parser fix. Listing pages already use
 * latest-per-product so they don't suffer this. We redirect the detail
 * page to the latest snapshot when one exists.
 */
function latestSnapshotIdIfDifferent(
  currentId: number,
  history: Array<{ id: number; scraped_at: string }> | undefined,
): number | null {
  if (!history || history.length === 0) return null;
  // API returns history ordered by scraped_at desc. Trust that, but be
  // defensive: take the actual max id we see (id is monotonic per crawl).
  let latest = history[0];
  for (const h of history) {
    if (
      h.scraped_at > latest.scraped_at ||
      (h.scraped_at === latest.scraped_at && h.id > latest.id)
    ) {
      latest = h;
    }
  }
  return latest.id !== currentId ? latest.id : null;
}

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

  // Stale-snapshot guard. If a newer offer row exists for the same
  // product (crawler ran since this row was created), forward to it so
  // the URL is effectively canonical-per-product. SEO-friendly 308.
  const newerId = latestSnapshotIdIfDifferent(offer.id, offer.history);
  if (newerId) {
    redirect(`/offers/${newerId}`);
  }

  const { product, brand, price, original_price, discount_pct, promo_label, currency, valid_from, valid_to, history } = offer;
  const promoBadge: string | null = promo_label
    ? promo_label
    : discount_pct != null && discount_pct > 0
      ? `-${discount_pct}%`
      : null;
  const savings =
    original_price != null && original_price > price ? original_price - price : null;

  return (
    <article className="flex flex-col gap-6">
      <nav className="text-sm text-ink-muted">
        <Link
          href="/offers"
          className="transition-colors hover:text-brand"
        >
          ← Όλες οι προσφορές
        </Link>
      </nav>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        <div className="relative aspect-square overflow-hidden rounded-[var(--radius-soft)] bg-canvas shadow-raised-lg">
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
            <div className="flex h-full w-full items-center justify-center text-7xl text-ink-muted/40">
              <span aria-hidden>🛒</span>
            </div>
          )}
          {promoBadge && (
            <span className="absolute left-3 top-3 rounded-full bg-accent px-3 py-1 text-sm font-bold uppercase tracking-wide text-white shadow-sm">
              {promoBadge}
            </span>
          )}
        </div>

        <div className="flex flex-col gap-4">
          <BrandChip
            brand={brand}
            href={`/brand/${brand.slug}`}
            size="md"
          />
          <h1 className="text-3xl font-bold tracking-tight text-ink">{product.name}</h1>
          {product.category && (
            <p className="text-sm text-ink-muted">{product.category}</p>
          )}
          {product.unit && (
            <p className="text-sm text-ink-soft">
              Συσκευασία: {product.unit}
            </p>
          )}

          <div className="flex items-baseline gap-3">
            <span className="text-4xl font-bold text-ink">
              {formatPrice(price, currency)}
            </span>
            {original_price != null && original_price > price && (
              <span className="text-xl text-ink-muted line-through">
                {formatPrice(original_price, currency)}
              </span>
            )}
          </div>
          {savings != null && (
            <p className="inline-flex w-fit items-center rounded-full bg-accent-soft px-3 py-1 text-sm font-semibold text-accent-hover">
              Εξοικονομείς {formatPrice(savings, currency)}
            </p>
          )}

          <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm text-ink-soft">
            {valid_from && (
              <>
                <dt className="text-ink-muted">Ισχύς από</dt>
                <dd>{formatDate(valid_from)}</dd>
              </>
            )}
            {valid_to && (
              <>
                <dt className="text-ink-muted">Ισχύς έως</dt>
                <dd>
                  {formatDate(valid_to)}{" "}
                  <span className="text-xs text-ink-muted">
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
              className="mt-2 inline-flex items-center justify-center rounded-[var(--radius-soft-pill)] bg-accent px-5 py-2.5 text-sm font-semibold text-white shadow-raised-accent transition-shadow hover:bg-accent-hover active:shadow-inset focus:outline-none focus-visible:ring-2 focus-visible:ring-brand"
            >
              Δες στο {brand.name} ↗
            </a>
          )}

          {product.canonical_product_id != null && (
            <Link
              href={`/compare/${product.canonical_product_id}`}
              className="inline-flex items-center justify-center rounded-[var(--radius-soft-pill)] bg-canvas px-5 py-2.5 text-sm font-semibold text-brand shadow-raised transition-shadow hover:shadow-raised-lg active:shadow-inset focus:outline-none focus-visible:ring-2 focus-visible:ring-brand"
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
