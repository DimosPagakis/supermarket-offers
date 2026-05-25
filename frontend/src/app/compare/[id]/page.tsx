import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { notFound } from "next/navigation";
import { BrandChip } from "@/components/BrandChip";
import { PriceComparisonTable } from "@/components/PriceComparisonTable";
import { fetchBrands, fetchCanonicalProduct } from "@/lib/api";
import { formatPrice } from "@/lib/format";

async function loadCanonical(idRaw: string) {
  const id = Number(idRaw);
  if (!Number.isFinite(id) || id <= 0) return null;
  try {
    return await fetchCanonicalProduct(id);
  } catch {
    return null;
  }
}

export async function generateMetadata(
  { params }: PageProps<"/compare/[id]">,
): Promise<Metadata> {
  const { id } = await params;
  const product = await loadCanonical(id);
  if (!product) return { title: "Σύγκριση προϊόντος" };

  const savingsPct =
    product.max_price > 0
      ? Math.round((product.price_savings / product.max_price) * 100)
      : 0;
  const title = `${product.display_name} — Συγκρίνετε τιμές σε ${product.brands_count} αλυσίδες`;
  const description = `Από ${formatPrice(product.min_price)}. Εξοικονομείτε ${formatPrice(
    product.price_savings,
  )}${savingsPct > 0 ? ` (${savingsPct}%)` : ""}${product.cheapest_brand ? ` ψωνίζοντας στην ${product.cheapest_brand.name}` : ""}.`;

  return {
    title,
    description,
    openGraph: {
      title,
      description,
      images: product.image_url ? [{ url: product.image_url }] : undefined,
      type: "website",
    },
  };
}

export default async function CompareDetailPage({
  params,
}: PageProps<"/compare/[id]">) {
  const { id } = await params;
  const [product, allBrands] = await Promise.all([
    loadCanonical(id),
    fetchBrands(),
  ]);
  if (!product) notFound();

  const {
    display_name,
    image_url,
    manufacturer_brand,
    size_value,
    size_unit,
    pack_count,
    variant_descriptor,
    category,
    brands_count,
    min_price,
    max_price,
    price_savings,
    offers,
    cheapest_brand,
  } = product;

  const sizeLabel = (() => {
    if (size_value == null || !size_unit) return null;
    const sized = `${size_value}${size_unit}`;
    return pack_count > 1 ? `${pack_count}×${sized}` : sized;
  })();

  const savingsPct =
    max_price > 0 ? Math.round((price_savings / max_price) * 100) : 0;

  // "Στις άλλες αλυσίδες" — brands we know about that don't currently carry
  // this canonical. Helps users discover gaps. If `brands_count === offers
  // .length === allBrands.length` there are no "other" chains.
  const presentSlugs = new Set(offers.map((o) => o.brand.slug));
  const missingBrands = allBrands.filter((b) => !presentSlugs.has(b.slug));

  return (
    <article className="flex flex-col gap-8">
      <nav className="text-sm text-ink-soft">
        <Link href="/compare" className="hover:text-brand transition-colors">
          ← Όλες οι συγκρίσεις
        </Link>
      </nav>

      {/* Hero */}
      <section className="grid grid-cols-1 gap-6 md:grid-cols-2">
        <div className="relative aspect-square overflow-hidden rounded-[var(--radius-soft)] bg-canvas shadow-raised-lg">
          {image_url ? (
            <Image
              src={image_url}
              alt={display_name}
              fill
              sizes="(max-width: 768px) 100vw, 50vw"
              className="object-contain p-6"
              priority
            />
          ) : (
            <div className="flex h-full w-full items-center justify-center text-7xl text-ink-muted">
              <span aria-hidden>🛒</span>
            </div>
          )}
          <span
            className={`absolute left-3 top-3 rounded-full px-3 py-1 text-sm font-bold ${
              brands_count >= 5
                ? "bg-warn-soft text-ink"
                : "bg-brand-fade text-brand"
            }`}
          >
            Διαθέσιμο σε {brands_count} αλυσίδες
          </span>
        </div>

        <div className="flex flex-col gap-4">
          <div className="flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center rounded-full bg-canvas px-3 py-1 text-xs font-semibold text-ink-soft shadow-raised-sm">
              {manufacturer_brand}
            </span>
            {category && (
              <span className="text-xs text-ink-muted">{category}</span>
            )}
          </div>

          <h1 className="text-2xl font-bold tracking-tight text-ink">{display_name}</h1>

          <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
            {sizeLabel && (
              <>
                <dt className="text-ink-muted">Συσκευασία</dt>
                <dd className="text-ink">{sizeLabel}</dd>
              </>
            )}
            {variant_descriptor && (
              <>
                <dt className="text-ink-muted">Παραλλαγή</dt>
                <dd className="text-ink">{variant_descriptor}</dd>
              </>
            )}
          </dl>

          <div className="mt-2 flex flex-col gap-1 rounded-[var(--radius-soft)] bg-canvas p-5 shadow-raised">
            <p className="text-xs uppercase tracking-wide text-accent-hover font-semibold">
              Εξοικονομείς έως
            </p>
            <p className="text-3xl font-bold text-accent">
              {formatPrice(price_savings)}
              {savingsPct > 0 && (
                <span className="ml-2 text-base font-medium text-accent-hover">
                  ({savingsPct}%)
                </span>
              )}
            </p>
            <p className="text-sm text-ink-soft">
              {price_savings > 0 ? (
                <>
                  Από {formatPrice(min_price)} (
                  <span className="font-semibold text-ink">{cheapest_brand?.name ?? "—"}</span>) έως {formatPrice(max_price)}.
                </>
              ) : (
                <>Όλες οι αλυσίδες έχουν την ίδια τιμή: {formatPrice(min_price)}.</>
              )}
            </p>
          </div>
        </div>
      </section>

      {/* Table */}
      <section className="flex flex-col gap-3">
        <h2 className="text-xl font-semibold tracking-tight">
          Σύγκριση τιμών ανά αλυσίδα
        </h2>
        <PriceComparisonTable offers={offers} />
      </section>

      {/* Missing brands */}
      {missingBrands.length > 0 && (
        <section className="flex flex-col gap-3">
          <h2 className="text-lg font-semibold tracking-tight">
            Στις άλλες αλυσίδες
          </h2>
          <p className="text-sm text-ink-soft">
            Δεν εντοπίσαμε ενεργή προσφορά για αυτό το προϊόν στις παρακάτω
            αλυσίδες. Δείτε τι προσφέρουν τώρα:
          </p>
          <ul className="flex flex-wrap gap-2">
            {missingBrands.map((b) => (
              <li key={b.slug}>
                <BrandChip brand={b} href={`/brand/${b.slug}`} size="md" />
              </li>
            ))}
          </ul>
        </section>
      )}
    </article>
  );
}
