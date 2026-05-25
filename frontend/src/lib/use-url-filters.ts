"use client";

/**
 * Shared URL-search-params plumbing for client-side filter bars.
 *
 * Both `OffersFiltersBar` and `CanonicalFiltersBar` need to translate
 * user interactions into navigations while React is mid-transition.
 * The hook owns:
 *
 *   - `pendingSearchRef` — the last URL we *intended* to commit,
 *     synchronously updated so rapid clicks compose instead of
 *     clobbering each other via the stale `useSearchParams` snapshot.
 *   - the resync effect that keeps the ref aligned with browser
 *     back/forward and external pushes.
 *   - `updateParam(mutate)` — gives callers a `URLSearchParams` they
 *     can imperatively edit; the hook handles `page` reset,
 *     ref commit, `startTransition`, and the scroll-stable
 *     `router.push`.
 *   - `reset(opts)` — wipes every key not listed in `preserve`.
 *
 * The hook is unit-tested directly via `renderHook`; the filter bars
 * are smoke-tested at the DOM level for the integration that matters
 * (CanonicalFiltersBar.test.tsx). See
 * docs/architecture/use-url-filters.md.
 */

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useRef, useTransition } from "react";

export type UseUrlFiltersOptions = {
  /**
   * Search-param keys that survive `reset()`. Both bars currently
   * preserve `q` so the global search box doesn't get cleared by the
   * filter-bar reset. Default: `["q"]`.
   */
  preserveOnReset?: ReadonlyArray<string>;
};

export type UpdateParam = (mutate: (sp: URLSearchParams) => void) => void;
export type Reset = () => void;

export type UseUrlFiltersResult = {
  /** True while the underlying `router.push` is in a pending transition. */
  pending: boolean;
  /**
   * Apply an imperative edit to the URL search-params. `page` is
   * always cleared (filter changes always start at page 1). Triggers
   * a scroll-stable `router.push` inside `startTransition`.
   */
  updateParam: UpdateParam;
  /** Wipe every search-param except those listed in `preserveOnReset`. */
  reset: Reset;
};

/**
 * Toggle membership of `value` in a CSV-encoded URL param (`?brand=ab,lidl`).
 * Exposed as a pure helper so callers can keep the mutate function tidy.
 */
export function toggleInCsv(csv: string | null, value: string): string {
  const set = new Set(
    (csv ?? "")
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean),
  );
  if (set.has(value)) set.delete(value);
  else set.add(value);
  return Array.from(set).join(",");
}

export function useUrlFilters(
  options: UseUrlFiltersOptions = {},
): UseUrlFiltersResult {
  const { preserveOnReset = ["q"] } = options;

  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [pending, startTransition] = useTransition();

  // Track the last URL we *intended* to navigate to, regardless of
  // whether the router has finished committing it. Rapid clicks (e.g.
  // brand chip + min-brands pill, fired in the same tick) must
  // compose: each handler needs to see the *pending* URL, not the one
  // in `searchParams` (held by React's transition snapshot) nor the
  // one in `window.location` (which the router updates asynchronously
  // after the transition commits).
  const pendingSearchRef = useRef<string>(`?${searchParams.toString()}`);
  useEffect(() => {
    pendingSearchRef.current = `?${searchParams.toString()}`;
  }, [searchParams]);

  const updateParam = useCallback<UpdateParam>(
    (mutate) => {
      const sp = new URLSearchParams(pendingSearchRef.current);
      mutate(sp);
      // Filter changes always restart pagination — keeping page=N
      // would silently land users on an empty page after narrowing.
      sp.delete("page");
      const qs = sp.toString();
      // Commit to the ref *synchronously* so the very next click in
      // the same tick reads this URL as its base, instead of
      // clobbering it.
      pendingSearchRef.current = qs ? `?${qs}` : "";
      startTransition(() => {
        // `push` (not `replace`) so browser back/forward step through
        // the filter history. `scroll: false` keeps the user anchored
        // to the grid — without it Next would jump the viewport to
        // the top on every filter change and the bar would appear
        // unresponsive.
        router.push(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
      });
    },
    [router, pathname],
  );

  const reset = useCallback<Reset>(() => {
    updateParam((sp) => {
      // Snapshot preserved values *before* deletion. Collect keys
      // first — `URLSearchParams.forEach` + `delete` mutate the
      // underlying list mid-iteration and skip entries.
      const preserved = new Map<string, string>();
      for (const key of preserveOnReset) {
        const v = sp.get(key);
        if (v != null) preserved.set(key, v);
      }
      const keys = Array.from(sp.keys());
      for (const key of keys) sp.delete(key);
      for (const [key, value] of preserved) sp.set(key, value);
    });
  }, [updateParam, preserveOnReset]);

  return { pending, updateParam, reset };
}
