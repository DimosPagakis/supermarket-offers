import type { Metadata } from "next";
import { CanonicalListView } from "@/components/CanonicalListView";
import {
  fetchBrands,
  fetchCanonicalProducts,
  fetchCategories,
} from "@/lib/api";
import { parseCanonicalQuery } from "@/lib/search-params";

export const metadata: Metadata = {
  title: "Σύγκριση τιμών — όλα τα προϊόντα",
  description:
    "Συγκρίνετε τιμές των ίδιων προϊόντων σε όλα τα ελληνικά σούπερ μάρκετ. Βρείτε πού πωλείται φθηνότερα το αγαπημένο σας brand.",
};

export default async function ComparePage({
  searchParams,
}: PageProps<"/compare">) {
  const raw = await searchParams;
  const query = parseCanonicalQuery(raw);
  const merged = {
    ...query,
    per_page: query.per_page ?? 24,
    min_brands: query.min_brands ?? 2,
  };

  const [page, brands, categories] = await Promise.all([
    fetchCanonicalProducts(merged),
    fetchBrands(),
    fetchCategories(),
  ]);

  return (
    <CanonicalListView
      query={merged}
      page={page}
      brands={brands}
      categories={categories}
      basePath="/compare"
      heading={
        <header className="flex flex-col gap-1">
          <h1 className="text-2xl font-bold tracking-tight">Σύγκριση τιμών</h1>
          {query.q ? (
            <p className="text-sm text-ink-soft">
              Αποτελέσματα για: <span className="font-medium">{query.q}</span>
            </p>
          ) : (
            <p className="text-sm text-ink-soft">
              Τα ίδια προϊόντα, σε όλες τις αλυσίδες — δείτε πού κοστίζει
              λιγότερο.
            </p>
          )}
        </header>
      }
    />
  );
}
