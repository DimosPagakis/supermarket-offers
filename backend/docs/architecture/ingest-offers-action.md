# IngestOffers action

## Context

`CrawlRunOfferController::store` is a ~70-line method that orchestrates
four concerns: a transaction, per-offer `ProductResolver::resolve()`,
one `Offer::create()` per item linked to the run, counter bookkeeping,
and an outer `Throwable` envelope emitting the `offer_push_failed` 500.

The pure business logic — "given a validated payload and a run, mutate
DB state and report counts" — is the same shape
`BulkUpsertCanonicalProducts` already extracted to: a transactional
batch write whose only outputs are integer counts. Today it cannot be
invoked outside the HTTP boundary, so a future artisan replay tool
(`offers:replay --from-dump`) would have to duplicate the orchestration.

## Decision

Extract into an invokable `App\Domain\Offer\IngestOffers`. It takes
the `CrawlRun` and the validated `offers` array and returns an
`IngestResult` DTO with `persisted`, `productsCreated`,
`productsUpdated`. The action runs inside its own `DB::transaction` —
any caller inherits the all-or-nothing rollback contract for free. It
re-raises on failure so the controller's existing 500 envelope keeps
working. `ProductResolver` is constructor-injected into the action and
dropped from the controller. Wire shape unchanged. Same precedent as
`docs/architecture/bulk-upsert-action.md`.

## Trade-offs

- Two new files plus a controller import. Indirection cost low.
- Transaction moves inside the action. Worth it: callers cannot
  invoke this without the rollback contract.
- No interface. One implementation; `$this->mock(ProductResolver::class)`
  still works in feature tests. Lift when a second algorithm arrives.
- Unlike the canonical case we add a small unit suite at
  `tests/Unit/Domain/Offer/IngestOffersTest.php` proving the action
  is independently usable (resolver branch + rollback). Feature
  tests remain the HTTP contract.
