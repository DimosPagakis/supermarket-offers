# MatchMethod enum

## Context

`products.canonical_match_method` is a string column whose acceptable
values — `rule`, `embedding`, `llm`, `manual` — are duplicated as a
hand-typed list inside `BulkUpsertCanonicalProductsRequest::rules()`
(`Rule::in(['rule', 'embedding', 'llm', 'manual'])`). The CanonicalProduct
controller stores `$member['match_method']` straight onto the model.
Tests sprinkle the literal `'rule'` in fixtures.

The current setup means:

- Adding a fifth method (e.g. `rerank`) requires editing the
  FormRequest, scanning every test, and trusting that no other call
  site forgot to widen.
- Application code never sees a typed handle on the method — it's
  always a raw string.

The canonicaliser side is about to ship a hybrid path that combines
rule + embedding signals, which is exactly the kind of moment where
the set of valid values changes.

## Decision

Introduce `App\Domain\Canonical\MatchMethod` — a PHP 8.1 string-backed
enum with cases `Rule`, `Embedding`, `Llm`, `Manual`. The FormRequest
swaps `Rule::in([...])` for `Rule::enum(MatchMethod::class)` so the
allowed-values list lives in one place. No schema change — the column
stays a string and the controller still writes the same wire value
(`$member['match_method']`) since `Rule::enum` accepts the case's
`->value`.

## Trade-offs

- One new file in `app/Domain/Canonical/`. Justified: this is the
  single source of truth for the canonical-side method taxonomy.
- A `Domain/` namespace appears for the first time. The cost is mental
  ("where does this live?"); the gain is that future canonical-side
  types (e.g. `Confidence` value objects) have an obvious home, and we
  avoid polluting `Models/` with non-Eloquent classes.
- Application code that pattern-matches on the method (none today) can
  use `match` over enum cases — strictly better than string compares.
- We deliberately do NOT cast `Product::canonical_match_method` to the
  enum yet — that would change the JSON wire shape on read endpoints
  that surface this column. None do today, but the conservative move
  keeps the column as a string and lets domain code opt in to the enum
  at the call site.
