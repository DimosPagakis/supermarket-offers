import { CanonicalFiltersBar } from "./CanonicalFiltersBar";
import { CanonicalGrid } from "./CanonicalGrid";
import { EmptyState } from "./EmptyState";
import { Pagination } from "./Pagination";
import type {
  Brand,
  CanonicalProductsPage,
  CanonicalQuery,
} from "@/lib/types";
import { toCanonicalSearchString } from "@/lib/search-params";

type Props = {
  query: CanonicalQuery;
  page: CanonicalProductsPage;
  brands: Brand[];
  categories: string[];
  basePath: string;
  heading?: React.ReactNode;
};

/**
 * Compare-catalogue layout. Filters live in a horizontal bar above the
 * grid so the catalogue gets the full page width — comparison cards
 * benefit from breathing room and a wider grid than the sidebar layout
 * allowed.
 */
export function CanonicalListView({
  query,
  page,
  brands,
  categories,
  basePath,
  heading,
}: Props) {
  const hrefForPage = (p: number) => {
    const qs = toCanonicalSearchString({ ...query, page: p });
    return qs ? `${basePath}?${qs}` : basePath;
  };

  return (
    <div className="flex flex-col gap-6">
      {heading}

      <CanonicalFiltersBar
        brands={brands}
        categories={categories}
        maxBrands={Math.max(2, brands.length)}
      />

      <div className="flex items-center justify-between text-sm text-ink-soft">
        <span>
          {page.meta.total > 0
            ? `${page.meta.total.toLocaleString("el-GR")} προϊόντα προς σύγκριση`
            : "Κανένα συγκρίσιμο προϊόν"}
        </span>
        {page.meta.last_page > 1 && (
          <span>
            Σελίδα {page.meta.current_page} από {page.meta.last_page}
          </span>
        )}
      </div>

      {page.data.length === 0 ? (
        <EmptyState
          title="Κανένα συγκρίσιμο προϊόν"
          message="Δοκίμασε λιγότερα φίλτρα ή χαμηλότερο όριο αλυσίδων."
        />
      ) : (
        <CanonicalGrid products={page.data} />
      )}

      <Pagination
        currentPage={page.meta.current_page}
        lastPage={page.meta.last_page}
        hrefForPage={hrefForPage}
      />
    </div>
  );
}
