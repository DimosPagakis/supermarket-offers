# Brand-colour fallback is part of the contract

## Context

`lib/brand-colours.ts` maps a brand slug (e.g. `ab`, `lidl`) to a triple
of hex values: `bg`, `fg`, `ring`. When the backend seeder adds a new
chain — or a crawler ships a brand that no-one has hand-tinted yet —
the slug arrives in the frontend with no entry in the `PALETTE` record.
A `FALLBACK` already exists; it returns a soft Picton tint that
matches the rest of the theme.

Two surfaces consume the fallback today: `BrandChip` (every card,
every comparison row, every brand link in the header) and both filter
bars (chip backgrounds when a brand is selected). If the fallback ever
regressed to `undefined` access, the UI would not crash silently — it
would crash loudly with `Cannot read properties of undefined`. The
graceful-fallback contract is therefore architecturally load-bearing
and deserves a pinned test, even though the production code is two
lines.

## Decision

Add a vitest test for `brandColour("unknown-slug")` that asserts:
- the function returns an object (never `undefined`),
- the shape matches `BrandColour` (all three keys are non-empty
  strings starting with `#`),
- a known slug round-trips the seeded entry unchanged.

No production code change. This is a test-only ADR — the pinning is
the architectural move.

## Trade-offs

- Cost: one extra test file (~25 lines). Minimal CI time.
- Benefit: any future refactor that accidentally returns `undefined`
  (e.g. a switch to `Map.get` without a `??`) fails locally instead of
  in production.
- Alternative considered: throw on unknown slug. Rejected — the
  product wants new chains to render *something* the moment the
  backend exposes them, before design has chosen a tint.
