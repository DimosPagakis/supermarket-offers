import { BrandChip } from "./BrandChip";
import { formatPrice } from "@/lib/format";
import type { FamilyVariant } from "@/lib/types";

type Props = {
  variant: FamilyVariant;
};

/**
 * One variant inside a family — e.g. "Africa" inside the Axe 150ml
 * family. Renders the descriptor as a row title and a small inline
 * mini-comparison: one chip per chain that stocks this variant,
 * ordered cheapest first.
 *
 * Empty `cheapest_brand` means none of the chain SKUs for this
 * variant currently has a valid offer — we still render the row so
 * shoppers see the variant exists, but the price block reads
 * "Χωρίς ενεργές προσφορές".
 */
export function FamilyVariantRow({ variant }: Props) {
  const {
    variant_descriptor,
    products,
    min_price,
    max_price,
    cheapest_brand,
  } = variant;

  const titled =
    variant_descriptor === "—"
      ? "Χωρίς παραλλαγή"
      : prettifyDescriptor(variant_descriptor);

  return (
    <article
      className="flex flex-col gap-3 rounded-[var(--radius-soft)] bg-canvas p-4 shadow-raised"
      data-testid="family-variant-row"
    >
      <header className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="text-base font-semibold text-ink">{titled}</h3>
        {min_price !== null && (
          <p className="text-sm text-ink-soft">
            <span className="font-bold text-ink">
              από {formatPrice(min_price)}
            </span>
            {max_price !== null && max_price > min_price && (
              <span className="ml-2 text-ink-muted line-through">
                {formatPrice(max_price)}
              </span>
            )}
            {cheapest_brand && (
              <span className="ml-2 text-ink-muted">
                στην <span className="font-medium text-ink">{cheapest_brand.name}</span>
              </span>
            )}
          </p>
        )}
      </header>

      <ul className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {products.map((product) => (
          <li
            key={product.id}
            className="flex flex-col gap-1.5 rounded-[var(--radius-soft)] bg-canvas p-3 shadow-inset"
          >
            <div className="flex items-center justify-between gap-2">
              <BrandChip brand={product.brand} size="sm" />
              {product.offer?.price !== undefined &&
                product.offer?.price !== null && (
                  <span className="text-lg font-bold text-ink">
                    {formatPrice(product.offer.price)}
                  </span>
                )}
            </div>
            <p
              className="line-clamp-2 text-[12px] text-ink-soft"
              title={product.name}
            >
              {product.name}
            </p>
            {product.offer?.discount_pct ? (
              <p className="text-[11px] font-semibold text-accent">
                -{product.offer.discount_pct}%
                {product.offer.original_price && (
                  <span className="ml-1.5 text-ink-muted line-through">
                    {formatPrice(product.offer.original_price)}
                  </span>
                )}
              </p>
            ) : null}
            {product.url && (
              <a
                href={product.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-[11px] text-brand hover:underline"
              >
                Δες στο κατάστημα →
              </a>
            )}
          </li>
        ))}
      </ul>
    </article>
  );
}

/**
 * The descriptor we store is a hyphen-joined slug of accent-folded
 * tokens — fine for the URL, ugly in the UI. Quick prettify pass:
 * replace `-` with spaces and capitalise the first letter so a row
 * titled `"africa-aposmhtiko-sprei"` becomes `"Africa aposmhtiko sprei"`.
 * If/when we add a localised display label per family this falls back
 * to the slug, which is at least readable to a developer.
 */
function prettifyDescriptor(descriptor: string): string {
  const cleaned = descriptor.replace(/-/g, " ").trim();
  if (cleaned === "") return descriptor;
  return cleaned.charAt(0).toUpperCase() + cleaned.slice(1);
}
