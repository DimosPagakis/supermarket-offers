import { EmptyState } from "./EmptyState";
import { FamilyGrid } from "./FamilyGrid";
import { Pagination } from "./Pagination";
import { toFamilySearchString } from "@/lib/search-params";
import type { FamiliesPage, FamilyQuery } from "@/lib/types";

type Props = {
  query: FamilyQuery;
  page: FamiliesPage;
  basePath: string;
  heading?: React.ReactNode;
};

/**
 * Catalogue layout for /families. Keeps the same chrome as
 * CanonicalListView (count line + pagination) but skips the filters
 * bar — the family-browse MVP exposes filters through the URL only,
 * since the parallel `feat/offers-default-discount` agent owns the
 * OffersFiltersBar territory we deliberately don't touch.
 */
export function FamilyListView({ query, page, basePath, heading }: Props) {
  const hrefForPage = (p: number) => {
    const qs = toFamilySearchString({ ...query, page: p });
    return qs ? `${basePath}?${qs}` : basePath;
  };

  return (
    <div className="flex flex-col gap-6">
      {heading}

      <div className="flex items-center justify-between text-sm text-ink-soft">
        <span>
          {page.meta.total > 0
            ? `${page.meta.total.toLocaleString("el-GR")} οικογένειες προϊόντων`
            : "Καμία οικογένεια δεν ταιριάζει"}
        </span>
        {page.meta.last_page > 1 && (
          <span>
            Σελίδα {page.meta.current_page} από {page.meta.last_page}
          </span>
        )}
      </div>

      {page.data.length === 0 ? (
        <EmptyState
          title="Καμία οικογένεια"
          message="Δοκίμασε λιγότερα φίλτρα ή χαμηλότερο όριο παραλλαγών."
        />
      ) : (
        <FamilyGrid families={page.data} />
      )}

      <Pagination
        currentPage={page.meta.current_page}
        lastPage={page.meta.last_page}
        hrefForPage={hrefForPage}
      />
    </div>
  );
}
