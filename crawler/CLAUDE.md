# Crawler — Working Notes for Claude

Project: Python Scrapy crawler that scrapes Greek supermarket weekly offers and
ships them to the Laravel backend via the `/api/v1/*` contract.

> **MVP-lean**: bloat-free, fast iteration. Add complexity via small PRs only
> when a real spider needs it. No proxy pools, no UA rotation, no anti-detection
> magic until a brand actually blocks us.

---

## Testing philosophy

**Favour integration tests over unit tests** — but unit tests are welcome where
they earn their keep (pure functions, parsers, normalizers).

### Where to put each kind

- **Unit tests** (`tests/test_normalize.py`, `tests/test_backend_client.py`):
  reserved for **pure logic** with no I/O — price parsing, date parsing,
  payload shaping, HTTP client behaviour against `httpx.MockTransport`. These
  are cheap, fast, and catch real bugs in parsers (Greek decimal commas, "Από
  DD.MM" date ranges, etc.). Keep adding them as we encounter parsing edge
  cases.
- **Integration tests** (preferred for new spider work): use Scrapy's built-in
  `parse` testing helpers or VCR-style cassettes of real HTML against frozen
  fixtures (`tests/fixtures/<brand>/<page>.html`). Run the spider's parse
  callback against the saved HTML and assert it yields the expected items.
  These catch selector drift — which is what actually breaks scrapers in
  production. Prefer this style over mocking out Scrapy internals.
- **End-to-end smoke tests** (manual, not in CI yet): boot the backend on
  `localhost:8000`, mint a token via `php artisan crawler:token`, set
  `BACKEND_URL` + `BACKEND_TOKEN`, run `scrapy crawl <spider>` and inspect
  the DB. Document the procedure in this file when we automate it.

### Anti-patterns we avoid

- Heavy mocking of Scrapy `Spider` internals — brittle, breaks on framework
  upgrades, doesn't test what we care about (selector correctness).
- Hitting the live supermarket sites in CI — rate-limit hostile, flaky, and
  blocks deployments when the site is down.
- Unit-testing the `BackendPipeline` by stubbing every Scrapy hook — capture
  it in an integration test instead.

---

## Architecture decisions worth remembering

### Why Scrapy + scrapy-playwright (hybrid)

`scrapy` for static HTML chains (Lidl, My Market). Cheap, fast, built-in
throttling, robots.txt, HTTP cache. Playwright for JS-rendered chains
(AB Vassilopoulos, Sklavenitis, Masoutis) — the listings only render after
JS executes. The strategy lives on each brand's `crawl_config.strategy`
column in the backend; the spider reads it via `BACKEND_URL` + token, no
hard-coding per brand.

### Why the BackendPipeline is dev-tolerant

If `BACKEND_URL` or `BACKEND_TOKEN` is missing the pipeline logs items
instead of crashing. This lets us iterate on selectors against real HTML
without booting the backend every time. Set both env vars for end-to-end
runs.

### Why `tenacity` only retries 5xx and network errors, not 4xx

4xx means our payload is wrong (validation, expired token, unknown run_id).
Retrying won't fix that — it'll just hammer the backend with the same bad
request. Fail fast, log the response body, let the operator investigate.

### Why the Lidl spider does a homepage → campaign-pages crawl

Lidl's weekly flyer URLs include a week-specific slug (e.g. `26kw22`) that
rotates every Thursday. Hard-coding it means weekly seed updates. The current
spider starts at the homepage (`https://www.lidl-hellas.gr/`) — the most
stable URL on the site — and harvests every `/c/<theme>-{YY}kw{WW}/a<id>`
anchor it lists. Each campaign page embeds its products as
`data-grid-data="<HTML-entity-encoded JSON>"` attributes which the parser
in `scraper/parsers/lidl.py` decodes.

(The older flyer-landing-page strategy in `/c/fylladio-lidl/s10020481`
turned out to be an image-viewer with no parseable HTML.)

### Why Lidl's priced-offer count is *expected* to swing 5×-fold week to week

A single weekly run can yield anywhere from 25 to 100+ priced offers
depending on:
* whether the Thursday rollover already happened (last-week campaign
  URLs linger for ~24h with empty `regionsPrices` blocks);
* how many of the 30-odd published campaigns are themed banners
  (`alpen-fest-style`, `paidi-axesoyar`, …) with zero priced products;
* whether Lidl is mid-rollover and most active offers live under
  `regionsPrices.<region>.currentPrice` (running now) vs
  `futurePrices` (starting in a day or two).

The parser handles **both** `currentPrice` and `futurePrices` shapes —
the original PR shipped with only `futurePrices` handling, which
silently dropped the entire live catalogue once the rollover flipped
offers from "future" to "current" (incident 2026-05-25: count collapsed
from ~85 to 27 until `currentPrice` support was added). Both fixtures
are pinned in `tests/test_lidl_parser.py`.

Bottom line: a Lidl run reporting 20–30 offers is **not automatically a
regression**. Check the per-campaign INFO log (`yielded N offers from
<url>`) and the run's per-campaign breakdown before assuming a bug.
True regressions look like "every campaign yields 0 offers despite
non-zero `data-grid-data` counts" — which is exactly the signal the
parser's DEBUG `found {N} data-grid-data attributes` line surfaces.

### Why selectors that miss log a warning instead of crashing

A spider that crashes on the first selector miss is a spider that produces
zero offers and a red alert. A spider that warns and yields nothing is one
we can compare against yesterday's run to know exactly which selectors broke.
The right level of paranoia for an MVP.

---

## Conventions

- **Python 3.12+**, Pydantic v2, `httpx` for the backend client (sync — Scrapy
  pipelines are sync by default; don't fight the framework).
- **`OfferItem.to_payload()`** is the single source of truth for the wire
  shape. If the backend contract changes, change it there and let the type
  errors fan out.
- **One spider per brand**, named after the brand slug (`lidl`, `ab`, ...).
  Each spider sets `brand_id` so the pipeline can call
  `POST /api/v1/crawl-runs` with the right brand.
- **Logging via `loguru`** for our code, default Scrapy logging for framework
  events. Don't try to unify them.
- **`ROBOTSTXT_OBEY = True`** until a specific brand requires otherwise; if
  we ever disable it for a brand, document why in this file.

---

## Adding a new spider — checklist

1. Confirm the brand's `strategy` (scrapy vs playwright) and `start_url` in
   the backend `crawl_configs` table; update the seeder if it's wrong.
2. Save 1–2 real HTML pages under `tests/fixtures/<brand>/` for replay tests.
3. Write a parse integration test against the fixture first. Run it red.
4. Implement the spider until the test goes green.
5. Add unit tests only for any new pure-logic helpers (date formats etc.).
6. Smoke-run locally with the backend up; confirm offers land in the DB.
7. Update the brand-status table in `README.md`.

---

## Brand status — discounted-only emit policy (2026-05-25)

All per-brand parsers now gate emit on a "real promo signal" — at
least one of `discount_pct > 0`, `original_price > price`, or a
non-null `promo_label`. The crawler refuses to leak the chain's
full catalogue into the public `/offers` endpoint:

| Brand       | Status                | Signal                                                                 |
|-------------|-----------------------|------------------------------------------------------------------------|
| ab          | active, gold standard | classified by `_classify_and_build` family (SHT / BXG% / BXGY / EUROS) |
| lidl        | active                | `discount.percentageDiscount > 0` / minus-prefixed `discountText` / `oldPrice > price` |
| masoutis    | active                | `Discount` starts with `-` / `StartPrice > PosPrice` (NOT `OfferDescr` — it's populated on catalogue rows too) |
| my-market   | active                | `span.diagonal-line` strikethrough OR `.offer-note--percent` pill |
| sklavenitis | **inactive**          | only `.sign-badges` "N+M Δώρο" badge — too narrow; deferred pending a real flyer URL |

If a parser is rewritten and the count crashes to near-zero, check
the per-brand signal column first before assuming selector drift.

## Things to push back on if the user asks for them

- Proxy pools, residential IPs, UA rotation — defer until we actually get
  blocked.
- Async pipeline — Scrapy's pipeline hooks are sync; switching to async
  Scrapy buys nothing for a 5-brand MVP.
- Heavy ORM-style item models — Pydantic is enough.
- A scheduler inside the crawler — Laravel owns scheduling, we are
  HTTP-triggered (or `scrapy crawl` from cron in early MVP).
