# Considered-and-rejected architectural moves

A record of candidate moves the May-2026 architecture pass evaluated
and decided NOT to ship. Future maintainers asking "should I introduce
X here?" should read this first — the answer was probably "no, and
here is why."

Update this file (don't delete entries) when the reasoning changes.

## Repository pattern over Eloquent

**Considered**: wrap `Brand`, `Product`, `Offer`, `CanonicalProduct`
behind `*Repository` interfaces and inject those instead of touching
the model statically.

**Rejected because**: Laravel's idiom is direct Eloquent at call
sites. Our controllers are mostly Eloquent against query builders
with brand-aware filters; the repository wrappers would either be
near-empty pass-throughs or grow into a parallel ORM. Tests already
use the SQLite in-memory DB (faster + closer to production semantics
than any mock). Adding a repository layer adds ~10 files for zero
behavioural improvement and one new mental model to keep straight.

## ProductResolverInterface

**Considered**: `App\Contracts\ProductResolverInterface` so the
canonical-write path can swap a different matching algorithm in.

**Rejected because**: one production implementation, one test mock
(`$this->mock(ProductResolver::class, …)` works fine against the
concrete class). PHP's container resolves the concrete type. No call
site benefits from polymorphism today. The cosmetic "feels more
SOLID" gain costs an extra file and a binding. Lift the interface
when the second algorithm actually arrives.

## Action classes for `StartCrawlRun` / `UpdateCrawlRun`

**Considered**: pull `CrawlRunController::store` and `::update` out
into invokable actions, mirroring `BulkUpsertCanonicalProducts`.

**Rejected because**: those controller methods are 6 and 15 lines
respectively — pure assignment from the validated payload onto an
Eloquent model. There is no orchestration, no transaction, no
branching worth its own file. CLAUDE.md's "keep controllers thin"
already holds here; thinner would be ceremonial.

## Domain events (`CrawlRunCompleted`, `OffersIngested`, `CanonicalsAssigned`)

**Considered**: emit framework events at the boundary of each
write so future consumers (cache invalidation, search index
sync, webhook fan-out) can subscribe without touching the writer.

**Rejected because**: there is exactly one consumer of each signal
today — and that consumer is the synchronous response. Events with
zero subscribers are dead code that look architectural. The category
list cache invalidation (which would be the first genuine subscriber)
is a single `Cache::forget` call; introduce the event the day the
second subscriber lands.

## `OfferListItem` DTO separating read-model from `OfferResource`

**Considered**: an explicit DTO between the Eloquent model and the
API resource, so the resource consumes a typed shape rather than
`@mixin Offer`.

**Rejected because**: the resource layer is already that read-model.
`OfferResource` decides what is public-facing; the controller decides
what gets eager-loaded. A DTO between them duplicates field lists for
no read-side benefit. The internal vs public split is enforced by the
two separate Resource trees (`Http/Resources/` vs
`Http/Resources/Public/`) — that is already a DTO pattern in
disguise.

## Shared "transactional bulk write" trait/wrapper for the two write
endpoints

**Considered**: dedupe the `try { DB::transaction(...) } catch
(Throwable) { Log + 500 envelope }` pattern between
`CrawlRunOfferController` and `CanonicalProductController` via a
trait or invokable middleware.

**Rejected because**: the error envelopes differ (`offer_push_failed`
vs `canonical_bulk_upsert_failed`) and the log context differs.
After Move 2 extracted the canonical action, the transaction
boundary already lives inside the action — so the controller's
try/catch is *just* the envelope formatter. Two sites × seven lines
each is below the dedup bar. If a third all-or-nothing bulk endpoint
ships, lift the shared envelope then.

## IoC for `Process::run` in `CrawlerDispatchCommand`

**Considered**: wrap the `Process::run` invocation behind a
`ProcessDispatcher` interface so the dispatch command is unit-
testable without `Process::fake`.

**Rejected because**: `Process::fake()` *is* the seam Laravel
provides, and the existing
`tests/Feature/Console/CrawlerDispatchCommandTest.php` exercises it
end-to-end. The shell-pipeline assertions in that test (`nohup`,
`> ... 2>&1 &`) are testing the exact thing a `ProcessDispatcher`
interface would hide, so the abstraction would weaken coverage, not
strengthen it.

## `LatestOfferPerProduct` query object

**Considered**: lift the MAX(id) GROUP BY product_id pattern out of
`Offer::latestPerProductIds` into a dedicated query class that
encapsulates both the offers-list and the canonical-list pricing
decorator call sites.

**Rejected because**: the static method on `Offer` is already that
abstraction. Two callers, both pass in a pre-filtered Builder and
plug the result into `whereIn('offers.id', …)`. A query class would
add a file and an `__invoke` indirection while exposing the same
surface. The composition shape (`whereIn` over the subquery) is the
sweet spot for SQLite + Postgres portability and is well-documented
on the static.

## Caching strategy / read-through layer

**Considered**: introduce a cache abstraction so list endpoints
(`/offers`, `/canonical-products`) can transparently serve a cached
payload, the way `/categories` already does.

**Rejected because**: only `/categories` warrants caching today (the
distinct-categories query is the cheapest possible to recompute, but
it is also the only response where the cache key is request-
independent). Offers vary by ~12 query parameters; any real cache
would need a paginator-aware varied-key scheme that we do not yet
have a workload for. Add cache when load tells us we need it, not
before.
