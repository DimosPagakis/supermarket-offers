"use client";

import { useRouter, useSearchParams, usePathname } from "next/navigation";
import { useCallback, useMemo, useState, useTransition } from "react";
import { brandColour } from "@/lib/brand-colours";
import type { Brand, CanonicalSortField } from "@/lib/types";

type Props = {
  brands: Brand[];
  categories: string[];
  /** Hard upper bound for `min_brands` — usually the number of chains we crawl. */
  maxBrands?: number;
};

function toggleInCsv(csv: string | null, value: string): string {
  const set = new Set(
    (csv ?? "").split(",").map((s) => s.trim()).filter(Boolean),
  );
  if (set.has(value)) set.delete(value);
  else set.add(value);
  return Array.from(set).join(",");
}

const SORT_OPTIONS: Array<{ value: CanonicalSortField; label: string }> = [
  { value: "brands_count", label: "Περισσότερες αλυσίδες" },
  { value: "members_count", label: "Περισσότερα μέλη" },
  { value: "display_name", label: "Αλφαβητικά" },
];

export function CanonicalFiltersSidebar({
  brands,
  categories,
  maxBrands = 5,
}: Props) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [pending, startTransition] = useTransition();

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

  const [minBrandsLocal, setMinBrandsLocal] = useState(minBrands);

  const updateParam = useCallback(
    (mutate: (sp: URLSearchParams) => void) => {
      const sp = new URLSearchParams(searchParams.toString());
      mutate(sp);
      sp.delete("page");
      const qs = sp.toString();
      startTransition(() => {
        router.replace(qs ? `${pathname}?${qs}` : pathname);
      });
    },
    [router, pathname, searchParams],
  );

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

  const onCommitMinBrands = (value: number) =>
    updateParam((sp) => {
      if (value > 2) sp.set("min_brands", String(value));
      else sp.delete("min_brands");
    });

  const onChangeSort = (sort: CanonicalSortField) =>
    updateParam((sp) => {
      if (sort === "brands_count") sp.delete("sort");
      else sp.set("sort", sort);
      // Sensible default dir per sort field.
      if (sort === "display_name") sp.set("dir", "asc");
      else sp.delete("dir");
    });

  const onReset = () => {
    updateParam((sp) => {
      const q = sp.get("q");
      sp.forEach((_, key) => sp.delete(key));
      if (q) sp.set("q", q);
    });
    setMinBrandsLocal(2);
  };

  return (
    <aside
      className={`flex flex-col gap-6 rounded-xl border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900 ${pending ? "opacity-70" : ""}`}
    >
      <div>
        <h3 className="mb-2 text-sm font-semibold text-zinc-700 dark:text-zinc-300">
          Αλυσίδα μέλος
        </h3>
        <div className="flex flex-wrap gap-2">
          {brands.map((b) => {
            const active = selectedBrands.has(b.slug);
            const colour = brandColour(b.slug);
            return (
              <button
                key={b.slug}
                type="button"
                onClick={() => onToggleBrand(b.slug)}
                aria-pressed={active}
                className="rounded-full px-3 py-1 text-xs font-medium transition"
                style={
                  active
                    ? { backgroundColor: colour.bg, color: colour.fg }
                    : {
                        backgroundColor: "transparent",
                        color: colour.bg,
                        border: `1px solid ${colour.bg}`,
                      }
                }
              >
                {b.name}
              </button>
            );
          })}
        </div>
      </div>

      <div>
        <label
          htmlFor="canon-category"
          className="mb-2 block text-sm font-semibold text-zinc-700 dark:text-zinc-300"
        >
          Κατηγορία
        </label>
        <select
          id="canon-category"
          value={selectedCategory}
          onChange={(e) => onChangeCategory(e.target.value)}
          className="w-full rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 focus:border-emerald-500 focus:outline-none dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-100"
        >
          <option value="">Όλες οι κατηγορίες</option>
          {categories.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
      </div>

      <div>
        <div className="mb-2 flex items-center justify-between">
          <label
            htmlFor="min_brands"
            className="text-sm font-semibold text-zinc-700 dark:text-zinc-300"
          >
            Ελάχιστος αριθμός αλυσίδων
          </label>
          <span className="text-sm text-zinc-600 dark:text-zinc-400">
            ≥ {minBrandsLocal}
          </span>
        </div>
        <input
          id="min_brands"
          type="range"
          min={2}
          max={maxBrands}
          step={1}
          value={minBrandsLocal}
          onChange={(e) => setMinBrandsLocal(Number(e.target.value))}
          onMouseUp={(e) =>
            onCommitMinBrands(Number((e.target as HTMLInputElement).value))
          }
          onTouchEnd={(e) =>
            onCommitMinBrands(Number((e.target as HTMLInputElement).value))
          }
          onKeyUp={(e) =>
            onCommitMinBrands(Number((e.target as HTMLInputElement).value))
          }
          className="w-full accent-emerald-600"
        />
        {minBrandsLocal >= maxBrands && (
          <p className="mt-1 text-xs text-amber-600">
            Σπάνιο — μόνο προϊόντα διαθέσιμα παντού.
          </p>
        )}
      </div>

      <div>
        <label
          htmlFor="canon-sort"
          className="mb-2 block text-sm font-semibold text-zinc-700 dark:text-zinc-300"
        >
          Ταξινόμηση
        </label>
        <select
          id="canon-sort"
          value={selectedSort}
          onChange={(e) => onChangeSort(e.target.value as CanonicalSortField)}
          className="w-full rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 focus:border-emerald-500 focus:outline-none dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-100"
        >
          {SORT_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      </div>

      <button
        type="button"
        onClick={onReset}
        className="text-xs font-medium text-zinc-500 underline hover:text-zinc-700 dark:hover:text-zinc-300"
      >
        Καθαρισμός φίλτρων
      </button>
    </aside>
  );
}
