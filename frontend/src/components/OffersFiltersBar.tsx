"use client";

import { useRouter, useSearchParams, usePathname } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useTransition } from "react";
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

const DISCOUNT_STEPS = [0, 10, 20, 30, 50] as const;

/**
 * Compact horizontal filter bar shared by `/`, `/offers`, and `/brand/[slug]`.
 * Mirrors the layout of `CanonicalFiltersBar` so the catalogue and the
 * comparison surface read as the same product. URL-driven, with the
 * `pendingSearchRef` synchronous-composition pattern so rapid multi-click
 * filters compose correctly through React's transition snapshot delay.
 */
export function OffersFiltersBar({ brands, categories, lockedBrand }: Props) {
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
  const validOnly = searchParams.get("has_discount") === "true";

  const activeCount =
    (lockedBrand ? 0 : selectedBrands.size > 0 ? 1 : 0) +
    (selectedCategory ? 1 : 0) +
    (minDiscount > 0 ? 1 : 0) +
    (validOnly ? 1 : 0);

  // Hold the URL we *intended* to navigate to, regardless of whether
  // React's transition has committed it yet. Without this, rapid clicks
  // in the same tick diff against the stale searchParams snapshot and
  // overwrite each other. Same pattern as CanonicalFiltersBar.
  const pendingSearchRef = useRef<string>(`?${searchParams.toString()}`);
  useEffect(() => {
    pendingSearchRef.current = `?${searchParams.toString()}`;
  }, [searchParams]);

  const updateParam = useCallback(
    (mutate: (sp: URLSearchParams) => void) => {
      const sp = new URLSearchParams(pendingSearchRef.current);
      mutate(sp);
      sp.delete("page");
      const qs = sp.toString();
      pendingSearchRef.current = qs ? `?${qs}` : "";
      startTransition(() => {
        router.push(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
      });
    },
    [router, pathname],
  );

  const onToggleBrand = (slug: string) => {
    if (lockedBrand) return;
    updateParam((sp) => {
      const next = toggleInCsv(sp.get("brand"), slug);
      if (next) sp.set("brand", next);
      else sp.delete("brand");
    });
  };

  const onChangeCategory = (cat: string) =>
    updateParam((sp) => {
      if (cat) sp.set("category", cat);
      else sp.delete("category");
    });

  const onChangeMinDiscount = (value: number) =>
    updateParam((sp) => {
      if (value > 0) sp.set("min_discount", String(value));
      else sp.delete("min_discount");
    });

  const onToggleValidOnly = () =>
    updateParam((sp) => {
      if (sp.get("has_discount") === "true") sp.delete("has_discount");
      else sp.set("has_discount", "true");
    });

  const onReset = () => {
    updateParam((sp) => {
      const q = sp.get("q");
      const keys = Array.from(sp.keys());
      for (const key of keys) sp.delete(key);
      if (q) sp.set("q", q);
    });
  };

  return (
    <section
      aria-label="Φίλτρα προσφορών"
      className={`bg-canvas rounded-[var(--radius-soft)] shadow-raised p-4 md:p-5 ${pending ? "opacity-70" : ""}`}
    >
      <div className="flex flex-wrap items-center gap-x-3 gap-y-3">
        {/* Brand chips */}
        {!lockedBrand && (
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
                    active ? "shadow-inset" : "shadow-raised-sm hover:shadow-raised"
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
        )}

        {!lockedBrand && (
          <div className="hidden h-6 w-px bg-border md:block" />
        )}

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

        {/* Min-discount pill stepper */}
        <fieldset className="flex items-center gap-2 text-xs font-semibold text-ink-soft">
          <legend className="contents">Έκπτωση ≥</legend>
          {DISCOUNT_STEPS.map((n) => {
            const active = minDiscount === n;
            return (
              <button
                key={n}
                type="button"
                onClick={() => onChangeMinDiscount(n)}
                aria-pressed={active}
                className={`min-w-[2.75rem] rounded-full px-2 py-1 text-xs font-semibold transition-shadow focus:outline-none focus-visible:ring-2 focus-visible:ring-brand ${
                  active
                    ? "shadow-inset text-brand"
                    : "shadow-raised-sm text-ink-soft hover:shadow-raised"
                }`}
              >
                {n === 0 ? "καμία" : `${n}%`}
              </button>
            );
          })}
        </fieldset>

        {/* Only-with-discount toggle chip */}
        <button
          type="button"
          onClick={onToggleValidOnly}
          aria-pressed={validOnly}
          className={`rounded-full px-3 py-1 text-xs font-semibold transition-shadow focus:outline-none focus-visible:ring-2 focus-visible:ring-brand ${
            validOnly
              ? "shadow-inset bg-accent text-white"
              : "shadow-raised-sm bg-canvas text-ink-soft hover:shadow-raised"
          }`}
        >
          Μόνο εκπτώσεις
        </button>

        {/* Reset chip */}
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
