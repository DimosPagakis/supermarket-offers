import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { OffersListView } from "@/components/OffersListView";
import {
  fetchBrandOffers,
  fetchBrands,
  fetchCategories,
} from "@/lib/api";
import { parseOfferQuery } from "@/lib/search-params";
import { brandColour } from "@/lib/brand-colours";

export async function generateMetadata(
  { params }: PageProps<"/brand/[slug]">,
): Promise<Metadata> {
  const { slug } = await params;
  const brands = await fetchBrands();
  const brand = brands.find((b) => b.slug === slug);
  if (!brand) return { title: "Αλυσίδα" };
  return {
    title: `Προσφορές ${brand.name}`,
    description: `Όλες οι ενεργές προσφορές από ${brand.name}.`,
  };
}

export default async function BrandPage({
  params,
  searchParams,
}: PageProps<"/brand/[slug]">) {
  const [{ slug }, raw] = await Promise.all([params, searchParams]);
  const brands = await fetchBrands();
  const brand = brands.find((b) => b.slug === slug);
  if (!brand) notFound();

  const query = parseOfferQuery(raw);
  const merged = { ...query, per_page: query.per_page ?? 50 };

  const [page, categories] = await Promise.all([
    fetchBrandOffers(slug, merged),
    fetchCategories(),
  ]);

  const colour = brandColour(brand.slug);

  return (
    <div className="flex flex-col gap-6">
      <div
        className="rounded-xl px-6 py-8 text-white shadow"
        style={{ backgroundColor: colour.bg, color: colour.fg }}
      >
        <h1 className="text-3xl font-bold">{brand.name}</h1>
        <p className="mt-1 text-sm opacity-90">
          Όλες οι ενεργές προσφορές · {page.meta.total.toLocaleString("el-GR")} προϊόντα
        </p>
        <a
          href={brand.website_url}
          target="_blank"
          rel="noreferrer noopener"
          className="mt-3 inline-block text-sm underline opacity-90 hover:opacity-100"
        >
          Επίσημος ιστότοπος ↗
        </a>
      </div>

      <OffersListView
        query={merged}
        page={page}
        brands={brands}
        categories={categories}
        basePath={`/brand/${slug}`}
        lockedBrand={slug}
      />
    </div>
  );
}
