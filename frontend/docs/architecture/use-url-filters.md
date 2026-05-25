# `useUrlFilters` — extract the shared URL-state plumbing

## Context

`OffersFiltersBar` and `CanonicalFiltersBar` are two client components
that share a non-trivial piece of infrastructure: keeping URL
search-params in sync with rapid user interaction while React is
mid-transition. The shared shape today, copy-pasted verbatim:

- a `pendingSearchRef` that mirrors the URL we *intended* to commit,
- a `useEffect` that resyncs the ref on `searchParams` change (back /
  forward / external push),
- an `updateParam(mutate)` callback that
  - reads the ref into `URLSearchParams`,
  - lets the caller mutate it,
  - deletes `page` (page-1 reset on every filter change),
  - writes the ref synchronously (so the next click in the same tick
    reads the just-applied URL),
  - calls `router.push(path?qs, { scroll: false })` inside
    `startTransition`,
- a `toggleInCsv` helper for multi-select chip groups,
- an `onReset` that wipes everything except `q`.

That is ~50 lines of pure logic duplicated across two files, and
neither bar can be unit-tested without spinning up jsdom and the
React testing library. There are exactly two call sites — the
threshold from the brief — and the next-feature scenario is concrete:
**a saved-search list page** would need the same plumbing the moment
it ships, lifting it ahead of that move makes the third call site
free.

## Decision

Introduce `src/lib/use-url-filters.ts` exposing
`useUrlFilters({ preserveOnReset })`. It returns
`{ pending, updateParam, reset, toggleInCsv }`. The hook owns the
ref, the resync effect, and the transition — but exposes the
`URLSearchParams` mutate interface unchanged, so neither bar needs a
behavioural rewrite. The CSV toggle helper, which was identical in
both files, lives on the hook namespace as a pure export.

Both filter bars switch to the hook. The CSV-toggle helper is
re-exported from the hook module so the bars don't reach for a
private utility.

Unit-test the hook directly via `renderHook` with a mocked
`next/navigation`. This is the testability win the brief asks for:
the URL-composition contract (page deletion, q preservation, ref
syncing, transition wrapping) can now be asserted without DOM clicks.

## Trade-offs

- Cost: one new file (~80 lines), one new test file. Both filter bar
  files shrink by ~30 lines each. Net code: ~+20 lines (the cost of
  the boundary).
- Indirection: a future reader of either bar must jump to the hook
  to see how URL state flows. Mitigated by keeping the hook in
  `src/lib/` (canonical destination for URL helpers, sibling to
  `search-params.ts`) and naming it after its job.
- Lock-in: now coupled to React's `useTransition` semantics — but
  both bars were already coupled. The hook makes the dependency
  explicit at one site rather than two.
- Rejected alternative: a `URL → URL` pure function that the bars
  consume with `useState`. Would not interoperate with
  `useTransition`'s pending flag, and would re-introduce the snapshot
  staleness bug the `pendingSearchRef` exists to solve.

## Future-proofing — concrete scenarios this unlocks

- A saved-search / pinned-filter page would consume the same hook
  with a different `preserveOnReset` set.
- Migrating from `?brand=ab,lidl` to multiple `?brand=ab&brand=lidl`
  needs only `toggleInCsv` and the serialiser to evolve; the hook
  itself stays.
- Adding a "clear-all-except-brand" affordance becomes a one-line
  helper on top of `reset`.
