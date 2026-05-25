import { OffersListView } from "@/components/OffersListView";
import { fetchBrands, fetchCategories, fetchOffers } from "@/lib/api";
import { parseOfferQuery } from "@/lib/search-params";

export default async function HomePage({ searchParams }: PageProps<"/">) {
  const raw = await searchParams;
  const query = parseOfferQuery(raw);
  // Homepage: top 50 discounts across all chains. Filters are still
  // available but the default sort is high-discount-first.
  const merged = {
    ...query,
    sort: query.sort ?? "discount_pct",
    dir: query.dir ?? ("desc" as const),
    has_discount: query.has_discount ?? true,
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
