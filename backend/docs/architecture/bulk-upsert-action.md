# BulkUpsertCanonicalProducts action

## Context

`CanonicalProductController::bulkUpsert` is a 130-line controller method
that orchestrates four concerns at once: (1) opening a transaction,
(2) per-grouping upsert by `canonical_key`, (3) per-member confidence
arbitration + cross-canonical "touch the previous canonical so its
aggregate gets refreshed" bookkeeping, (4) post-batch aggregate
refresh, plus an outer `Throwable` envelope.

The pure business logic — "given a validated payload, mutate DB state
and report counts" — is the load-bearing piece. It is also the
hardest to read, the part most likely to grow (the canonicaliser is
adding a re-scoring pass that will write at the same surface), and the
only piece worth feature-testing twice (we already have eight feature
tests covering it). Today it cannot be invoked outside the HTTP
boundary, so a hypothetical artisan-side replay tool (`canonical:rerun
--from-dump`) would have to duplicate the orchestration.

Compare with `ProductResolver`: that one already lives in `Services/`
and the controller is a thin transaction-shell around it. The
canonical side is the exception, not the rule.

## Decision

Extract the business logic into an invokable
`App\Domain\Canonical\BulkUpsertCanonicalProducts` action. It takes
the validated `groupings` array and returns a result DTO
(`BulkUpsertResult`) with `created`, `updated`, `productsAssigned`,
`errors`. The action runs inside its own `DB::transaction` — so any
caller (controller, artisan command, future event handler) gets the
all-or-nothing guarantee for free.

The controller becomes ~25 lines: pull validated data, call the
action, wrap the result in a JSON envelope, catch the outer Throwable
and emit the existing `canonical_bulk_upsert_failed` 500. Wire shape
unchanged.

## Trade-offs

- Two new files (action + result DTO) and the controller now imports
  them. Indirection cost: low — the names spell out what they do.
- The transaction moves inside the action. The controller no longer
  reads "transaction-wrapped"; that's named in the action's docblock
  instead. Worth it: callers should not be able to invoke this without
  the rollback contract.
- We do NOT add an interface. One implementation, no swap-in scenario
  worth speculation. The action is concrete; if a second algorithm
  arrives we'll lift the interface then.
- We do NOT add an event (`CanonicalsAssigned`) — no second consumer.
- Test seam unlocked: the action is now feature-testable directly
  (without HTTP) by callers that wire `DB::transaction`. We don't add
  that test today — the feature tests already cover the path
  end-to-end and per CLAUDE.md, "a unit test that re-asserts what a
  feature test already covers is dead weight."
