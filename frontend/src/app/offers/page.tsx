import type { Metadata } from "next";
import { OffersListView } from "@/components/OffersListView";
import { fetchBrands, fetchCategories, fetchOffers } from "@/lib/api";
import { parseOfferQuery } from "@/lib/search-params";

export const metadata: Metadata = {
  title: "Όλες οι προσφορές",
  description:
    "Φίλτραρε προσφορές σούπερ μάρκετ ανά αλυσίδα, κατηγορία και ποσοστό έκπτωσης.",
};

export default async function OffersPage({
  searchParams,
}: PageProps<"/offers">) {
  const raw = await searchParams;
  const query = parseOfferQuery(raw);
  // Default to newest-first sort so applying a discount filter visibly
  // shrinks the deck. With the backend's `discount_pct desc` default the
  // top of page-1 stays the same after toggling a filter (the highest-
  // discount items naturally satisfy any min_discount threshold), making
  // it look like the filter did nothing. `scraped_at desc` surfaces
  // recently-crawled offers, so the page-1 list materially changes when
  // a discount filter clips out items.
  const merged = {
    ...query,
    sort: query.sort ?? "scraped_at",
    dir: query.dir ?? ("desc" as const),
    per_page: query.per_page ?? 50,
  };

  const [page, brands, categories] = await Promise.all([
    fetchOffers(merged),
    fetchBrands(),
    fetchCategories(),
  ]);

  return (
    <OffersListView
      query={merged}
      page={page}
      brands={brands}
      categories={categories}
      basePath="/offers"
      heading={
        <header className="flex flex-col gap-1">
          <h1 className="text-3xl font-bold tracking-tight text-ink">Προσφορές</h1>
          {query.q ? (
            <p className="text-sm text-ink-soft">
              Αποτελέσματα για: <span className="font-medium text-ink">{query.q}</span>
            </p>
          ) : (
            <p className="text-sm text-ink-soft">
              Όλες οι ενεργές προσφορές. Χρησιμοποίησε τα φίλτρα για να εστιάσεις.
            </p>
          )}
        </header>
      }
    />
  );
}
