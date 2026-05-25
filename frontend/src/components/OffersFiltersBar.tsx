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
 * Combined (sort, dir) options surfaced to the user as a single dropdown.
 * The backend already exposes `sort=price|discount_pct|scraped_at` and
 * `dir=asc|desc` independently; collapsing them into a labelled menu
 * matches how shoppers actually think about it ("biggest discount", not
 * "discount_pct desc").
 */
const SORT_OPTIONS: ReadonlyArray<{
  key: string;
  label: string;
  sort: "scraped_at" | "discount_pct" | "price";
  dir: "asc" | "desc";
}> = [
  { key: "newest",          label: "Νεότερες πρώτα",      sort: "scraped_at", dir: "desc" },
  { key: "discount_desc",   label: "Μεγαλύτερη έκπτωση",  sort: "discount_pct", dir: "desc" },
  { key: "discount_asc",    label: "Μικρότερη έκπτωση",   sort: "discount_pct", dir: "asc" },
  { key: "price_asc",       label: "Φθηνότερα πρώτα",     sort: "price", dir: "asc" },
  { key: "price_desc",      label: "Ακριβότερα πρώτα",    sort: "price", dir: "desc" },
];

function sortOptionKey(sort: string | null, dir: string | null): string {
  const found = SORT_OPTIONS.find(
    (o) => o.sort === sort && o.dir === (dir ?? "desc"),
  );
  return found?.key ?? "";
}

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
  const currentSortKey = sortOptionKey(
    searchParams.get("sort"),
    searchParams.get("dir"),
  );

  const activeCount =
    (lockedBrand ? 0 : selectedBrands.size > 0 ? 1 : 0) +
    (selectedCategory ? 1 : 0) +
    (minDiscount > 0 ? 1 : 0) +
    (validOnly ? 1 : 0) +
    (currentSortKey && currentSortKey !== "newest" ? 1 : 0);

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

  const onChangeSort = (key: string) =>
    updateParam((sp) => {
      const opt = SORT_OPTIONS.find((o) => o.key === key);
      if (!opt) {
        sp.delete("sort");
        sp.delete("dir");
        return;
      }
      sp.set("sort", opt.sort);
      sp.set("dir", opt.dir);
    });

  const onReset = () => {
    updateParam((sp) => {
      const q = sp.get("q");
      const keys = Array.from(sp.keys());
      for (const key of keys) sp.delete(key);
      if (q) sp.set("q", q);
    });
  };

  // Close any open <details> popovers when clicking outside the bar.
  // Without this, the brand popover stays open until the next click on
  // the same summary — annoying when filters compose.
  const barRef = useRef<HTMLElement | null>(null);
  useEffect(() => {
    function onDown(e: MouseEvent) {
      if (!barRef.current) return;
      if (barRef.current.contains(e.target as Node)) return;
      barRef.current
        .querySelectorAll("details[open]")
        .forEach((d) => d.removeAttribute("open"));
    }
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
  }, []);

  const brandSummary =
    selectedBrands.size === 0
      ? "Όλες"
      : selectedBrands.size === 1
        ? (brands.find((b) => b.slug === [...selectedBrands][0])?.name ?? "1 επιλογή")
        : `${selectedBrands.size} επιλεγμένες`;

  const discountSummary =
    minDiscount > 0 ? `≥ ${minDiscount}%` : "Όλες";

  return (
    <section
      ref={barRef}
      aria-label="Φίλτρα προσφορών"
      className={`bg-canvas rounded-[var(--radius-soft)] shadow-raised p-4 md:p-5 ${pending ? "opacity-70" : ""}`}
    >
      <div className="flex flex-wrap items-center gap-x-3 gap-y-3">
        {/* Brands — multi-select popover */}
        {!lockedBrand && (
          <details className="relative">
            <summary
              className="flex cursor-pointer list-none items-center gap-2 rounded-[var(--radius-soft)] bg-canvas px-3 py-1.5 text-xs font-semibold text-ink-soft shadow-inset focus-visible:ring-2 focus-visible:ring-brand"
              aria-label={`Αλυσίδες: ${brandSummary}`}
            >
              <span>Αλυσίδες</span>
              <span className="font-normal text-ink">{brandSummary}</span>
              <span aria-hidden className="text-ink-muted">▾</span>
            </summary>
            <div
              role="group"
              className="absolute left-0 top-[calc(100%+0.5rem)] z-30 flex min-w-[14rem] flex-col gap-1 rounded-[var(--radius-soft)] bg-canvas p-2 shadow-raised-lg"
            >
              {brands.map((b) => {
                const active = selectedBrands.has(b.slug);
                const colour = brandColour(b.slug);
                return (
                  <button
                    key={b.slug}
                    type="button"
                    onClick={() => onToggleBrand(b.slug)}
                    aria-pressed={active}
                    className={`flex items-center gap-2 rounded-[var(--radius-soft-pill)] px-3 py-1.5 text-left text-xs font-medium transition-shadow focus:outline-none focus-visible:ring-2 focus-visible:ring-brand ${
                      active ? "shadow-inset" : "hover:shadow-raised-sm"
                    }`}
                    style={
                      active
                        ? { backgroundColor: colour.bg, color: colour.fg }
                        : undefined
                    }
                  >
                    <span
                      className="inline-block h-2 w-2 shrink-0 rounded-full"
                      style={{ backgroundColor: colour.bg }}
                      aria-hidden
                    />
                    <span className="flex-1 truncate">{b.name}</span>
                    {active && (
                      <span aria-hidden className="text-base leading-none">
                        ✓
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          </details>
        )}

        {/* Category dropdown — narrower, with `max-w` so it can't eat the bar. */}
        <label className="flex items-center gap-2 text-xs font-semibold text-ink-soft">
          Κατηγορία
          <select
            value={selectedCategory}
            onChange={(e) => onChangeCategory(e.target.value)}
            className="max-w-[10rem] truncate rounded-[var(--radius-soft)] bg-canvas px-3 py-1.5 text-sm font-normal text-ink shadow-inset focus:outline-none focus-visible:ring-2 focus-visible:ring-brand"
          >
            <option value="">Όλες</option>
            {categories.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </label>

        {/* Min-discount dropdown — single threshold (lower bound). The ≥
            prefix in each label keeps the semantics unambiguous. */}
        <label className="flex items-center gap-2 text-xs font-semibold text-ink-soft">
          Έκπτωση
          <select
            value={minDiscount > 0 ? String(minDiscount) : ""}
            onChange={(e) =>
              onChangeMinDiscount(e.target.value ? Number(e.target.value) : 0)
            }
            className="rounded-[var(--radius-soft)] bg-canvas px-3 py-1.5 text-sm font-normal text-ink shadow-inset focus:outline-none focus-visible:ring-2 focus-visible:ring-brand"
            aria-label={`Ελάχιστη έκπτωση: ${discountSummary}`}
          >
            <option value="">Όλες</option>
            {DISCOUNT_STEPS.filter((n) => n > 0).map((n) => (
              <option key={n} value={String(n)}>
                ≥ {n}%
              </option>
            ))}
          </select>
        </label>

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

        {/* Sort dropdown — collapses (sort, dir) into a single labelled
            choice. Empty value falls back to the server-side default
            per page (e.g. newest on /offers, biggest discount on /). */}
        <label className="flex items-center gap-2 text-xs font-semibold text-ink-soft">
          Ταξινόμηση
          <select
            value={currentSortKey}
            onChange={(e) => onChangeSort(e.target.value)}
            className="rounded-[var(--radius-soft)] bg-canvas px-3 py-1.5 text-sm font-normal text-ink shadow-inset focus:outline-none focus-visible:ring-2 focus-visible:ring-brand"
          >
            <option value="">Προεπιλογή</option>
            {SORT_OPTIONS.map((o) => (
              <option key={o.key} value={o.key}>
                {o.label}
              </option>
            ))}
          </select>
        </label>

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
