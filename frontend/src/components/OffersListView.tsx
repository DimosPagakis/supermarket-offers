import { FiltersSidebar } from "./FiltersSidebar";
import { OfferGrid } from "./OfferGrid";
import { EmptyState } from "./EmptyState";
import { Pagination } from "./Pagination";
import type { Brand, OffersPage } from "@/lib/types";
import { toSearchString } from "@/lib/search-params";
import type { OfferQuery } from "@/lib/types";

type Props = {
  /** The currently-applied filters (already parsed from the URL). */
  query: OfferQuery;
  page: OffersPage;
  brands: Brand[];
  categories: string[];
  /** Base path to append paginated links to. */
  basePath: string;
  /** Locks the brand filter to a single slug (brand pages). */
  lockedBrand?: string;
  heading?: React.ReactNode;
};

export function OffersListView({
  query,
  page,
  brands,
  categories,
  basePath,
  lockedBrand,
  heading,
}: Props) {
  const hrefForPage = (p: number) => {
    const qs = toSearchString({ ...query, page: p });
    return qs ? `${basePath}?${qs}` : basePath;
  };

  return (
    <div className="flex flex-col gap-6 lg:flex-row">
      <div className="lg:w-64 lg:shrink-0">
        <FiltersSidebar
          brands={brands}
          categories={categories}
          lockedBrand={lockedBrand}
        />
      </div>

      <div className="flex min-w-0 flex-1 flex-col gap-4">
        {heading}
        <div className="flex items-center justify-between text-sm text-ink-soft">
          <span>
            {page.meta.total > 0
              ? `${page.meta.total.toLocaleString("el-GR")} προσφορές`
              : "Καμία προσφορά"}
          </span>
          {page.meta.last_page > 1 && (
            <span>
              Σελίδα {page.meta.current_page} από {page.meta.last_page}
            </span>
          )}
        </div>

        {page.data.length === 0 ? (
          <EmptyState />
        ) : (
          <OfferGrid offers={page.data} />
        )}

        <Pagination
          currentPage={page.meta.current_page}
          lastPage={page.meta.last_page}
          hrefForPage={hrefForPage}
        />
      </div>
    </div>
  );
}
