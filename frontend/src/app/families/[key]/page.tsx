import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { notFound } from "next/navigation";
import { FamilyVariantRow } from "@/components/FamilyVariantRow";
import { fetchFamily } from "@/lib/api";
import { formatPrice } from "@/lib/format";

async function loadFamily(keyRaw: string) {
  if (!keyRaw) return null;
  const key = decodeURIComponent(keyRaw);
  try {
    return await fetchFamily(key);
  } catch {
    return null;
  }
}

export async function generateMetadata({
  params,
}: PageProps<"/families/[key]">): Promise<Metadata> {
  const { key } = await params;
  const family = await loadFamily(key);
  if (!family) return { title: "Παραλλαγές προϊόντος" };

  const title = `${family.display_name} — ${family.variants_count} παραλλαγές σε προσφορά`;
  const fromCopy =
    family.min_price !== null
      ? `Από ${formatPrice(family.min_price)} σε ${family.brands_count} αλυσίδες.`
      : "";
  return {
    title,
    description: `${fromCopy} Δες όλες τις διαθέσιμες επιλογές για ${family.display_name}.`,
    openGraph: {
      title,
      description: fromCopy,
      images: family.image_url ? [{ url: family.image_url }] : undefined,
      type: "website",
    },
  };
}

export default async function FamilyDetailPage({
  params,
}: PageProps<"/families/[key]">) {
  const { key } = await params;
  const family = await loadFamily(key);
  if (!family) notFound();

  const {
    display_name,
    image_url,
    manufacturer_brand,
    size_value,
    size_unit,
    pack_count,
    category,
    variants_count,
    brands_count,
    min_price,
    max_price,
    avg_price,
    variants,
  } = family;

  const sizeLabel = (() => {
    if (size_value == null || !size_unit) return null;
    const sized = `${size_value}${size_unit}`;
    return pack_count > 1 ? `${pack_count}×${sized}` : sized;
  })();

  const spread =
    min_price !== null && max_price !== null
      ? Math.max(0, max_price - min_price)
      : 0;

  return (
    <article className="flex flex-col gap-8">
      <nav className="text-sm text-ink-soft">
        <Link
          href="/families"
          className="hover:text-brand transition-colors"
        >
          ← Όλες οι οικογένειες
        </Link>
      </nav>

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
          <span className="absolute left-3 top-3 rounded-full bg-brand-fade px-3 py-1 text-sm font-bold text-brand">
            {variants_count} παραλλαγές
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

          <h1 className="text-2xl font-bold tracking-tight text-ink">
            {display_name}
          </h1>

          <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
            {sizeLabel && (
              <>
                <dt className="text-ink-muted">Συσκευασία</dt>
                <dd className="text-ink">{sizeLabel}</dd>
              </>
            )}
            <dt className="text-ink-muted">Αλυσίδες</dt>
            <dd className="text-ink">{brands_count}</dd>
            <dt className="text-ink-muted">Παραλλαγές</dt>
            <dd className="text-ink">{variants_count}</dd>
          </dl>

          {min_price !== null && (
            <div className="mt-2 flex flex-col gap-1 rounded-[var(--radius-soft)] bg-canvas p-5 shadow-raised">
              <p className="text-xs uppercase tracking-wide font-semibold text-accent-hover">
                Διακύμανση τιμής στην οικογένεια
              </p>
              <p className="text-3xl font-bold text-ink">
                {formatPrice(min_price)}
                {max_price !== null && max_price > min_price && (
                  <span className="ml-2 text-base font-medium text-ink-muted">
                    – {formatPrice(max_price)}
                  </span>
                )}
              </p>
              <p className="text-sm text-ink-soft">
                {avg_price !== null && (
                  <>
                    Μέσος όρος {formatPrice(avg_price)}
                    {spread > 0 && <> · διαφορά {formatPrice(spread)}</>}
                  </>
                )}
              </p>
            </div>
          )}
        </div>
      </section>

      <section className="flex flex-col gap-3">
        <h2 className="text-xl font-semibold tracking-tight">
          Όλες οι παραλλαγές σε προσφορά
        </h2>
        <ul className="flex flex-col gap-4">
          {variants.map((v) => (
            <li key={v.variant_descriptor}>
              <FamilyVariantRow variant={v} />
            </li>
          ))}
        </ul>
      </section>
    </article>
  );
}
