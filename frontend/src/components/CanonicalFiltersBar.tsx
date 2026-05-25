"use client";

import { useSearchParams } from "next/navigation";
import { useMemo } from "react";
import { brandColour } from "@/lib/brand-colours";
import { toggleInCsv, useUrlFilters } from "@/lib/use-url-filters";
import type { Brand, CanonicalSortField } from "@/lib/types";

type Props = {
  brands: Brand[];
  categories: string[];
  /** Hard upper bound for `min_brands` — usually the number of chains we crawl. */
  maxBrands?: number;
};

const SORT_OPTIONS: Array<{ value: CanonicalSortField; label: string }> = [
  { value: "brands_count", label: "Περισσότερες αλυσίδες" },
  { value: "members_count", label: "Περισσότερα μέλη" },
  { value: "display_name", label: "Αλφαβητικά" },
];

/**
 * Compact horizontal filter bar for /compare. Sits above the grid and gives
 * the catalogue back full page width. URL-driven, like the sidebar it
 * replaces. Tiny per-control palette: canvas surfaces, Picton focus rings,
 * French pink for the "clear" affordance only.
 */
export function CanonicalFiltersBar({
  brands,
  categories,
  maxBrands = 5,
}: Props) {
  const searchParams = useSearchParams();
  const { pending, updateParam, reset } = useUrlFilters();

  const selectedBrands = useMemo(
    () =>
      new Set(
        (searchParams.get("brand") ?? "")
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
      ),
    [searchParams],
  );
  const selectedCategory = searchParams.get("category") ?? "";
  const minBrands = Number(searchParams.get("min_brands") ?? "2");
  const selectedSort =
    (searchParams.get("sort") as CanonicalSortField | null) ?? "brands_count";

  // Derive the active min-brands value directly from the URL so the pill
  // selection stays in sync with browser back/forward navigation. The
  // previous local-state mirror would drift out of date on history pops.
  const activeCount =
    (selectedBrands.size > 0 ? 1 : 0) +
    (selectedCategory ? 1 : 0) +
    (minBrands > 2 ? 1 : 0) +
    (selectedSort !== "brands_count" ? 1 : 0);

  const onToggleBrand = (slug: string) =>
    updateParam((sp) => {
      const next = toggleInCsv(sp.get("brand"), slug);
      if (next) sp.set("brand", next);
      else sp.delete("brand");
    });

  const onChangeCategory = (cat: string) =>
    updateParam((sp) => {
      if (cat) sp.set("category", cat);
      else sp.delete("category");
    });

  const onChangeMinBrands = (value: number) => {
    updateParam((sp) => {
      if (value > 2) sp.set("min_brands", String(value));
      else sp.delete("min_brands");
    });
  };

  const onChangeSort = (sort: CanonicalSortField) =>
    updateParam((sp) => {
      if (sort === "brands_count") sp.delete("sort");
      else sp.set("sort", sort);
      if (sort === "display_name") sp.set("dir", "asc");
      else sp.delete("dir");
    });

  const onReset = reset;

  return (
    <section
      aria-label="Φίλτρα σύγκρισης"
      className={`bg-canvas rounded-[var(--radius-soft)] shadow-raised p-4 md:p-5 ${pending ? "opacity-70" : ""}`}
    >
      <div className="flex flex-wrap items-center gap-x-3 gap-y-3">
        {/* Brand chips — inline, tinted when selected. */}
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-semibold text-ink-soft mr-1">
            Αλυσίδες
          </span>
          {brands.map((b) => {
            const active = selectedBrands.has(b.slug);
            const colour = brandColour(b.slug);
            return (
              <button
                key={b.slug}
                type="button"
                onClick={() => onToggleBrand(b.slug)}
                aria-pressed={active}
                className={`rounded-full px-3 py-1 text-xs font-medium transition-shadow focus:outline-none focus-visible:ring-2 focus-visible:ring-brand ${
                  active
                    ? "shadow-inset"
                    : "shadow-raised-sm hover:shadow-raised"
                }`}
                style={
                  active
                    ? { backgroundColor: colour.bg, color: colour.fg }
                    : { backgroundColor: "var(--color-canvas)", color: "var(--color-ink-soft)" }
                }
              >
                {b.name}
              </button>
            );
          })}
        </div>

        {/* Vertical divider on wider screens */}
        <div className="hidden h-6 w-px bg-border md:block" />

        {/* Category dropdown */}
        <label className="flex items-center gap-2 text-xs font-semibold text-ink-soft">
          Κατηγορία
          <select
            value={selectedCategory}
            onChange={(e) => onChangeCategory(e.target.value)}
            className="rounded-[var(--radius-soft)] bg-canvas px-3 py-1.5 text-sm font-normal text-ink shadow-inset focus:outline-none focus-visible:ring-2 focus-visible:ring-brand"
          >
            <option value="">Όλες</option>
            {categories.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </label>

        {/* Min-brands stepper as a tiny pill group */}
        <fieldset className="flex items-center gap-2 text-xs font-semibold text-ink-soft">
          <legend className="contents">Σε ≥</legend>
          {Array.from({ length: Math.max(2, maxBrands) - 1 }, (_, i) => i + 2).map(
            (n) => (
              <button
                key={n}
                type="button"
                onClick={() => onChangeMinBrands(n)}
                aria-pressed={minBrands === n}
                className={`min-w-[2.25rem] rounded-full px-2 py-1 text-xs font-semibold transition-shadow focus:outline-none focus-visible:ring-2 focus-visible:ring-brand ${
                  minBrands === n
                    ? "shadow-inset text-brand"
                    : "shadow-raised-sm text-ink-soft hover:shadow-raised"
                }`}
              >
                {n}
              </button>
            ),
          )}
          <span className="ml-1 font-normal text-ink-muted">αλυσίδες</span>
        </fieldset>

        {/* Sort */}
        <label className="flex items-center gap-2 text-xs font-semibold text-ink-soft">
          Ταξινόμηση
          <select
            value={selectedSort}
            onChange={(e) => onChangeSort(e.target.value as CanonicalSortField)}
            className="rounded-[var(--radius-soft)] bg-canvas px-3 py-1.5 text-sm font-normal text-ink shadow-inset focus:outline-none focus-visible:ring-2 focus-visible:ring-brand"
          >
            {SORT_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </label>

        {/* Reset — visible only when at least one filter is active. */}
        {activeCount > 0 && (
          <button
            type="button"
            onClick={onReset}
            className="ml-auto rounded-full bg-accent-soft px-3 py-1 text-xs font-semibold text-accent-hover shadow-raised-sm transition-shadow hover:shadow-raised focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
          >
            Καθαρισμός ({activeCount})
          </button>
        )}
      </div>
    </section>
  );
}
