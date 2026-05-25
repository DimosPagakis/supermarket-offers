"use client";

import { useRouter, useSearchParams, usePathname } from "next/navigation";
import { useCallback, useMemo, useState, useTransition } from "react";
import { brandColour } from "@/lib/brand-colours";
import type { Brand } from "@/lib/types";

type Props = {
  brands: Brand[];
  categories: string[];
  /** Brand slug to lock the brand filter to (used on /brand/[slug]). */
  lockedBrand?: string;
};

function toggleInCsv(csv: string | null, value: string): string {
  const set = new Set(
    (csv ?? "").split(",").map((s) => s.trim()).filter(Boolean),
  );
  if (set.has(value)) set.delete(value);
  else set.add(value);
  return Array.from(set).join(",");
}

export function FiltersSidebar({ brands, categories, lockedBrand }: Props) {
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
  const minDiscount = Number(searchParams.get("min_discount") ?? "0");
  const validToday = searchParams.get("has_discount") === "true";

  const [minDiscountLocal, setMinDiscountLocal] = useState(minDiscount);

  // Count of currently-active filters (excludes locked brand + free-text q).
  const activeFilters =
    (lockedBrand ? 0 : selectedBrands.size) +
    (selectedCategory ? 1 : 0) +
    (minDiscount > 0 ? 1 : 0) +
    (validToday ? 1 : 0);

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

  const onToggleBrand = (slug: string) => {
    if (lockedBrand) return;
    updateParam((sp) => {
      const next = toggleInCsv(sp.get("brand"), slug);
      if (next) sp.set("brand", next);
      else sp.delete("brand");
    });
  };

  const onChangeCategory = (cat: string) => {
    updateParam((sp) => {
      if (cat) sp.set("category", cat);
      else sp.delete("category");
    });
  };

  const onCommitMinDiscount = (value: number) => {
    updateParam((sp) => {
      if (value > 0) sp.set("min_discount", String(value));
      else sp.delete("min_discount");
    });
  };

  const onToggleHasDiscount = () => {
    updateParam((sp) => {
      if (sp.get("has_discount") === "true") sp.delete("has_discount");
      else sp.set("has_discount", "true");
    });
  };

  const onReset = () => {
    updateParam((sp) => {
      const q = sp.get("q");
      sp.forEach((_, key) => sp.delete(key));
      if (q) sp.set("q", q);
    });
    setMinDiscountLocal(0);
  };

  return (
    <aside
      className={`flex flex-col gap-6 rounded-[var(--radius-card)] border border-border bg-surface p-4 shadow-card ${pending ? "opacity-70" : ""}`}
    >
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-ink">Φίλτρα</h2>
        {activeFilters > 0 && (
          <span
            className="inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-accent px-1.5 text-[10px] font-bold text-white"
            aria-label={`${activeFilters} ενεργά φίλτρα`}
          >
            {activeFilters}
          </span>
        )}
      </div>

      <div>
        <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-muted">
          Αλυσίδα
        </h3>
        <div className="flex flex-wrap gap-2">
          {brands.map((b) => {
            const active = lockedBrand
              ? b.slug === lockedBrand
              : selectedBrands.has(b.slug);
            const colour = brandColour(b.slug);
            return (
              <button
                key={b.slug}
                type="button"
                onClick={() => onToggleBrand(b.slug)}
                disabled={!!lockedBrand}
                aria-pressed={active}
                className={`rounded-full px-3 py-1 text-xs font-medium transition-colors disabled:cursor-not-allowed ${
                  active
                    ? "ring-2"
                    : "border border-border hover:bg-canvas-muted"
                }`}
                style={
                  active
                    ? {
                        backgroundColor: colour.bg,
                        color: colour.fg,
                        boxShadow: `inset 0 0 0 1px ${colour.ring}`,
                      }
                    : { color: "var(--color-ink-soft)" }
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
          htmlFor="category"
          className="mb-2 block text-xs font-semibold uppercase tracking-wide text-ink-muted"
        >
          Κατηγορία
        </label>
        <select
          id="category"
          value={selectedCategory}
          onChange={(e) => onChangeCategory(e.target.value)}
          className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-ink focus:border-brand focus:outline-none"
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
            htmlFor="min_discount"
            className="text-xs font-semibold uppercase tracking-wide text-ink-muted"
          >
            Ελάχιστη έκπτωση
          </label>
          <span className="text-sm font-medium text-ink">
            {minDiscountLocal}%
          </span>
        </div>
        <input
          id="min_discount"
          type="range"
          min={0}
          max={70}
          step={5}
          value={minDiscountLocal}
          onChange={(e) => setMinDiscountLocal(Number(e.target.value))}
          onMouseUp={(e) =>
            onCommitMinDiscount(Number((e.target as HTMLInputElement).value))
          }
          onTouchEnd={(e) =>
            onCommitMinDiscount(Number((e.target as HTMLInputElement).value))
          }
          onKeyUp={(e) =>
            onCommitMinDiscount(Number((e.target as HTMLInputElement).value))
          }
          className="w-full accent-brand"
        />
      </div>

      <label className="flex items-center gap-2 text-sm text-ink-soft">
        <input
          type="checkbox"
          checked={validToday}
          onChange={onToggleHasDiscount}
          className="h-4 w-4 rounded border-border accent-brand"
        />
        Μόνο με έκπτωση
      </label>

      {activeFilters > 0 && (
        <button
          type="button"
          onClick={onReset}
          className="rounded-full px-3 py-2 text-xs font-medium text-brand transition-colors hover:bg-brand-fade"
        >
          Καθαρισμός φίλτρων
        </button>
      )}
    </aside>
  );
}
