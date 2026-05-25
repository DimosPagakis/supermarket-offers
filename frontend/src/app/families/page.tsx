import type { Metadata } from "next";
import { FamilyListView } from "@/components/FamilyListView";
import { fetchFamilies } from "@/lib/api";
import { parseFamilyQuery } from "@/lib/search-params";

export const metadata: Metadata = {
  title: "Παραλλαγές προϊόντων — όλες οι επιλογές σε προσφορά",
  description:
    "Βρες όλες τις παραλλαγές ενός προϊόντος που είναι σε προσφορά: αρώματα, γεύσεις, αποχρώσεις — σε όλα τα ελληνικά σούπερ μάρκετ.",
};

export default async function FamiliesPage({
  searchParams,
}: PageProps<"/families">) {
  const raw = await searchParams;
  const query = parseFamilyQuery(raw);
  // Default per_page=24 (same as compare) and min_variants=2 — see
  // FamilyIndexRequest for the why. Server-side defaults ensure the
  // /families URL works without query params.
  const merged = {
    ...query,
    per_page: query.per_page ?? 24,
    min_variants: query.min_variants ?? 2,
  };

  const page = await fetchFamilies(merged);

  return (
    <FamilyListView
      query={merged}
      page={page}
      basePath="/families"
      heading={
        <header className="flex flex-col gap-1">
          <h1 className="text-2xl font-bold tracking-tight">
            Παραλλαγές προϊόντων
          </h1>
          {query.q ? (
            <p className="text-sm text-ink-soft">
              Αποτελέσματα για: <span className="font-medium">{query.q}</span>
            </p>
          ) : (
            <p className="text-sm text-ink-soft">
              Δες όλες τις παραλλαγές μιας οικογένειας προϊόντων που είναι σε
              προσφορά — αρώματα, γεύσεις, αποχρώσεις.
            </p>
          )}
        </header>
      }
    />
  );
}
