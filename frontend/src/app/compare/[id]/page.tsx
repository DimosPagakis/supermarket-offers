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
  )}${savingsPct > 0 ? ` (${savingsPct}%)` : ""} ψωνίζοντας στην ${product.cheapest_brand.name}.`;

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
      <nav className="text-sm text-zinc-500">
        <Link href="/compare" className="hover:text-emerald-600">
          ← Όλες οι συγκρίσεις
        </Link>
      </nav>

      {/* Hero */}
      <section className="grid grid-cols-1 gap-6 md:grid-cols-2">
        <div className="relative aspect-square overflow-hidden rounded-xl border border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-900">
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
            <div className="flex h-full w-full items-center justify-center text-7xl text-zinc-300 dark:text-zinc-700">
              <span aria-hidden>🛒</span>
            </div>
          )}
          <span
            className={`absolute left-3 top-3 rounded-md px-3 py-1 text-sm font-bold shadow ${
              brands_count >= 5
                ? "bg-amber-500 text-white"
                : "bg-emerald-600 text-white"
            }`}
          >
            Διαθέσιμο σε {brands_count} αλυσίδες
          </span>
        </div>

        <div className="flex flex-col gap-4">
          <div className="flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center rounded-full bg-zinc-100 px-3 py-1 text-xs font-medium text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300">
              {manufacturer_brand}
            </span>
            {category && (
              <span className="text-xs text-zinc-500">{category}</span>
            )}
          </div>

          <h1 className="text-2xl font-bold tracking-tight">{display_name}</h1>

          <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
            {sizeLabel && (
              <>
                <dt className="text-zinc-500">Συσκευασία</dt>
                <dd className="text-zinc-800 dark:text-zinc-200">{sizeLabel}</dd>
              </>
            )}
            {variant_descriptor && (
              <>
                <dt className="text-zinc-500">Παραλλαγή</dt>
                <dd className="text-zinc-800 dark:text-zinc-200">
                  {variant_descriptor}
                </dd>
              </>
            )}
          </dl>

          <div className="mt-2 flex flex-col gap-1 rounded-xl border border-emerald-200 bg-emerald-50 p-4 dark:border-emerald-900/40 dark:bg-emerald-900/20">
            <p className="text-xs uppercase tracking-wide text-emerald-700 dark:text-emerald-300">
              Εξοικονομείς έως
            </p>
            <p className="text-3xl font-bold text-emerald-700 dark:text-emerald-300">
              {formatPrice(price_savings)}
              {savingsPct > 0 && (
                <span className="ml-2 text-base font-medium">
                  ({savingsPct}%)
                </span>
              )}
            </p>
            <p className="text-sm text-emerald-800 dark:text-emerald-200">
              {price_savings > 0 ? (
                <>
                  Από {formatPrice(min_price)} (
                  <span className="font-semibold">{cheapest_brand.name}</span>) έως {formatPrice(max_price)}.
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
          <p className="text-sm text-zinc-600 dark:text-zinc-400">
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
