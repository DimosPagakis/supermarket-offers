# `parseOfferQuery` / `parseCanonicalQuery` is the URL contract

## Context

The frontend uses URL search-params as its source of truth for filter
state. Every page that lists offers or canonical products parses its
incoming `searchParams` through `parseOfferQuery` or
`parseCanonicalQuery` in `lib/search-params.ts`. These functions own
the *only* runtime check that the URL — which any user can craft —
maps to a `TypedQueryObject` the backend will accept.

Today the round-trip is covered:
- `buildOfferQueryString` / `buildCanonicalQueryString` have full
  vitest coverage in `api.test.ts`,
- `toSearchString` / `toCanonicalSearchString` are exercised
  indirectly through page-link generation.

But the **inbound** parsers — the boundary that protects the backend
from `?min_discount=NaN`, `?page=-3&sort=evil`, `?per_page=99999`,
arrays-via-repeat-keys — have **no direct tests**. A regression here
either ships invalid filters to the API or silently drops valid URLs
that came in from search engines / Slack-shared links / paste-able
filter URLs.

Considered extracting a `defineQuerySchema(spec).parse(raw)` helper.
Rejected — only two schemas exist, each with bespoke validation
ranges (`min_discount` 0–100, `min_brands` 1–10, sort enums). A
generic builder costs more in indirection than the duplication it
would remove, and no third schema is on the roadmap.

## Decision

Pin the inbound contract with a vitest suite that asserts:
- empty params → empty query,
- CSV brand splits to array, trims whitespace, drops empty members,
- `min_discount` / `min_brands` reject NaN, negatives, and
  out-of-range values,
- `has_discount` only honours literal `"true"` / `"false"`,
- `page` / `per_page` floor, reject ≤ 0, and clamp `per_page` at 100,
- sort enum gates unknown values,
- array-shaped params (`?brand=ab&brand=lidl`) take the first entry
  (`firstString`'s documented behaviour).

## Trade-offs

- Cost: ~80 lines of test code, no production change. Future
  parser tweaks must update the test — that's the point.
- Benefit: the URL contract becomes a refactor anchor. Anyone moving
  to a query-schema helper (Zod-style or hand-rolled) inherits a
  pass/fail target.
- Alternative considered: a property-based test with fast-check.
  Rejected — would add a dev dep for two pure functions; the
  enumerated cases above cover every branch.
