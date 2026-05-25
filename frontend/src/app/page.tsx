import { OffersListView } from "@/components/OffersListView";
import { fetchBrands, fetchCategories, fetchOffers } from "@/lib/api";
import { parseOfferQuery } from "@/lib/search-params";

export default async function HomePage({ searchParams }: PageProps<"/">) {
  const raw = await searchParams;
  const query = parseOfferQuery(raw);
  // Homepage: 50 offers sorted high-discount-first. We deliberately do
  // NOT force `has_discount=true` server-side even though the page
  // title implies it — a hidden default would silently override any
  // user toggle of "Μόνο εκπτώσεις" in the filter bar (the URL never
  // carries the value, so clicking the chip off has no observable
  // effect). The discount-desc sort already pushes real discounts to
  // the top; if a shopper wants strict "only with discount", the
  // chip in the bar is the canonical control and they'll see the
  // count drop accordingly.
  const merged = {
    ...query,
    sort: query.sort ?? "discount_pct",
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
      basePath="/"
      heading={
        <header className="flex flex-col gap-1">
          <h1 className="text-3xl font-bold tracking-tight text-ink">
            Οι μεγαλύτερες εκπτώσεις σήμερα
          </h1>
          <p className="text-sm text-ink-soft">
            Συγκεντρωμένες προσφορές από AB, Σκλαβενίτη, Lidl, My Market και Μασούτη.
          </p>
        </header>
      }
    />
  );
}
