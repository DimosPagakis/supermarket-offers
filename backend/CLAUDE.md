# Backend — Working Notes for Claude

Project: Laravel 12 backend for the Greek supermarket offer aggregator.
Owns the schema, all business logic, scheduling, and the public read-API
that the (future) frontend will consume. Talks to the Python crawler
exclusively over a versioned REST contract at `/api/v1/*`.

> **MVP-lean**: bloat-free, fast iteration. Add complexity via migrations
> only when needed. No JSON columns — relational tables only. No raw HTML
> snapshots — re-crawl if we need to reprocess. Greek market for now.

---

## Testing philosophy

**Strongly favour integration (feature) tests over unit tests.**

The backend is mostly a thin layer of validation + ORM writes + resource
shaping. Pure-logic islands worth unit-testing are rare. What we actually
need to verify is the **HTTP behaviour** — that the right request shape
hits the right endpoint, the right rows land in the DB, and the right
JSON comes back. Feature tests do that end-to-end through the framework
in milliseconds (SQLite in-memory), without mocking the things that
matter.

### Conventions

- **All new endpoints get a feature test under `tests/Feature/Api/`.**
  Extend `ApiTestCase` which already wires `RefreshDatabase` + a
  `authedAsCrawler()` helper that issues a Sanctum token with the
  `crawler:write` ability.
- **Cover three buckets per endpoint**, minimum:
  1. Auth — unauthenticated rejected, wrong ability rejected.
  2. Happy path — DB state matches expectations, response shape matches
     the API Resource.
  3. Validation — every meaningful business invariant has a red test
     (inactive brand, terminal run, value out of range, etc.).
- **Prefer asserting on `assertDatabaseHas` and model state over raw JSON
  paths** when checking that a write happened — JSON paths cover the
  contract, DB asserts cover the persistence.
- **Don't mock Eloquent.** If you find yourself reaching for
  `Mockery::mock(Brand::class)` you're testing the wrong layer; write a
  feature test instead.
- **Do mock collaborators that throw**, e.g. `$this->mock(ProductResolver::class, ...)`
  is the right tool to prove a transaction rolls back on exception.

### When a unit test is appropriate

- Pure helpers with no I/O — e.g. `StringNormalizer::normalize()` (Greek
  accent stripping). These can live in `tests/Unit/`.
- Don't reach for unit tests just to bump coverage. A unit test that
  re-asserts what a feature test already covers is dead weight.

### Anti-patterns we avoid

- Trying to test Eloquent itself — Laravel already tests its own ORM.
- Testing controllers in isolation by hand-constructing requests —
  use `postJson`/`patchJson` and route through the real middleware
  stack so auth, ability checks, FormRequests, and resources all run.
- Test fixtures that duplicate the seeder. If a test needs realistic
  brands, call the seeder; otherwise create the minimum row inline.

---

## Architecture decisions worth remembering

### Why the crawler owns crawl-run lifecycle (and the backend doesn't)

`CrawlRunOfferController` is a pure data sink — it persists offers and
returns counts. It deliberately does **not** mutate `crawl_runs.status`
on success or failure. The crawler is the single authority for run
lifecycle: it calls `POST /crawl-runs` to start, pushes offers, then
calls `PATCH /crawl-runs/{run}` to mark `success` / `failed` / `partial`
with final counts. Splitting authority would mean two places racing to
set `finished_at`. Keep one writer per piece of state.

### Why offer pushes are all-or-nothing (single DB transaction)

If a batch of 200 offers fails halfway through, we don't want 100
phantom offers in the DB with no clear way for the crawler to know what
landed. The transaction rolls back on any exception and the controller
returns a structured `500 offer_push_failed` with a `Safe to retry`
hint. The crawler retries the same batch — idempotent because product
matching is by `(brand_id, external_id)` or `(brand_id, normalized_name)`.

### Why ProductResolver lives in `app/Services/` and not on the model

Eloquent models are persistence containers. "Find or create a product,
update mutable fields, report whether it was new or modified" is
business logic with multiple branches and should be testable in
isolation. Services keep controllers thin and let us swap the
implementation (e.g. for the `canonical_product_id` unification work)
without touching every call site.

### Why FormRequests carry business invariants, not just shape rules

Type/range/format checks live in `rules()`. Cross-field rules
(`valid_to >= valid_from`), stateful rules (the run must still be
`running` to accept offers, an inactive brand can't be crawled), and
domain constraints (`offers_persisted <= offers_found`) live in
`withValidator()->after(...)`. Putting them anywhere else means the
controller has to remember to call them, and we'll forget.

### Why Sanctum personal-access tokens (not session/SPA)

The crawler is a machine client — it has no session, no CSRF, no
cookies. PAT with the `crawler:write` ability gives us a per-token
audit trail (`Sanctum::actingAs`) and lets us revoke individual
crawlers without nuking auth for everyone. `php artisan crawler:token`
mints one and prints the bearer string once.

### Why we route everything under `/api/v1/*`

We will absolutely break the contract once we see real spider output.
Versioning the route prefix from day one means we can ship a `/v2/`
alongside `/v1/` and let the crawler migrate on its own schedule.
Don't fold this in.

### Why no JSON columns, anywhere

JSON columns hide schema. We can't query them with simple `WHERE`,
migrations don't track changes inside them, and they invite "just dump
it in there" laziness. Every config is a real column or a real
relational child table. If a future config needs N variants per brand,
add a child table via migration.

### Why SQLite by default

MVP. Zero ops, file-backed, fast tests. PostgreSQL drop-in is
trivial when we need concurrent writes or JSONB-style queries. Don't
swap until a real workload demands it.

---

## Conventions

- **All endpoints versioned**: `/api/v1/*`. New endpoints go here until
  we explicitly cut `/v2/`.
- **All write endpoints use a FormRequest** in `app/Http/Requests/Api/V1/`.
  No raw `$request->validate()` in controllers.
- **All response shapes use an API Resource** in `app/Http/Resources/`.
  Controllers return resource instances or `response()->json(...)` for
  error envelopes; they never echo `$model->toArray()`.
- **Migrations are the schema source of truth.** When the model
  changes, write a new migration — never edit a shipped one.
- **Commit messages** follow Conventional Commits. Every commit gets
  the `Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>`
  trailer.

---

## Adding a new endpoint — checklist

1. Define the route under `/api/v1/*` with the right middleware
   (`auth:sanctum`, `ability:<scope>` if scoped).
2. Create a FormRequest. Put shape rules in `rules()`, business
   invariants in `withValidator()->after()`. Add a `messages()`
   override only when the default message would confuse a crawler
   engineer.
3. Create or extend a controller. Keep it thin — push branching and
   matching into a Service.
4. Create an API Resource for the response shape. Don't leak Eloquent
   accessors.
5. Write a feature test that covers auth + happy path + every business
   invariant you added.
6. Update `docs/api.md` with a curl example.
7. If the contract changed in a way the crawler must know about, flag
   it in the PR description so the crawler engineer can update their
   client.

---

## Things to push back on if the user asks for them

- **Adding a JSON column** "just for this one config" — relational table
  instead.
- **Storing raw scraped HTML/JSON snapshots** — we agreed: re-crawl if we
  need reprocessing.
- **Mocking Eloquent in feature tests** — the SQLite in-memory DB is
  faster than the mock setup, and tests real schema constraints.
- **Pagination on `GET /brands`** — five brands. Don't.
- **Throttling middleware on the API** — single crawler client. Add when
  we onboard a second consumer.
- **Telescope / Horizon / Pulse** — not until we have a real ops story.
- **A separate `users` table for crawler service accounts** — the
  default users table + a `crawler:write` ability is enough.
