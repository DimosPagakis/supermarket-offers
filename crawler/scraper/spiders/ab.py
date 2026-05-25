"""AB Vassilopoulos promotion spider.

AB exposes a Next.js storefront whose product catalogue is fetched
client-side from a GraphQL persisted-query endpoint at
``https://www.ab.gr/api/v1/``. We bypass Playwright entirely — the
spider hits the GraphQL endpoint with the same operation, variables,
and sha256 hash the browser uses.

The heavy mapping logic lives in ``scraper.parsers.ab`` and is
exercised against a committed fixture so we'd catch a schema change
in plain pytest before a live run.

Pagination
----------
AB's GraphQL ``ProductList`` query returns ``pagination.totalPages``
on every page; we paginate from 0 until ``totalPages`` is reached, or
``AB_MAX_PAGES`` is hit (whichever comes first). The cap is a
safety net for runaway catalogues only — the dynamic ``totalPages``
is the real stop condition. On 2026-05-25 the catalogue was 87 pages;
the cap is 120 to leave headroom.

When the cap clips real coverage the spider emits a ``WARNING`` line
that names ``CRAWLER_MAX_PAGES_AB`` — set that env var to a larger
integer to widen the cap without a code change.

Risks worth knowing about
-------------------------
* AB can rotate the persisted-query sha256 hash without warning.
  When that happens the API replies with ``PersistedQueryNotFound``.
  Mitigation today: the spider logs a clear error and yields
  nothing. Mitigation tomorrow (intentional follow-up): hit the
  storefront once via Playwright, grab the fresh hash from the
  network log, fall through.
* AB rate-limits aggressively per IP. ``DOWNLOAD_DELAY=2`` plus the
  default polite ``USER_AGENT`` keeps us well under the threshold
  in observed runs.

Follow-up: full-catalogue walk via ``CATEGORY``
-----------------------------------------------
A 2026-05-25 probe confirmed the same persisted-query hash also serves
``productListingType="CATEGORY"`` (e.g. ``categoryCode="008"`` →
totalResults=1385, paginated 10 at a time). Walking every top-level
category would catch products that AB chose not to surface on
``/search/promotions`` (regional offers, online-exclusive bundles).
However the gain over the broader-promotion fix shipped here is
unverified — most non-promotion products have a flat ``price.value``
with no Promotion attached and would have to be filtered back out to
keep "offers" meaningful. Implementing the walk = (a) seed a stable
list of category codes from AB's storefront sitemap, (b) iterate
~50 categories × up to ~140 pages each ≈ 7000 requests at
DOWNLOAD_DELAY=2 = ~4h crawl, (c) re-filter each product through
``_classify_and_build`` so loyalty / regular-price entries don't leak
through. Not MVP territory; revisit when a real customer signal says
AB is still under-shipping after the broader-promotion fix.
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, UTC
from typing import Any
from urllib.parse import urlencode

import scrapy
from loguru import logger
from scrapy.http import Response

from scraper.parsers.ab import EMITTED_FAMILIES, extract_offers_with_family
from scraper.spiders._config import max_pages_from_env

AB_GRAPHQL_URL = "https://www.ab.gr/api/v1/"

# Snapshot of the persisted-query hash used by the production storefront
# on 2026-05-25. Verified by capturing the live browser request to
# ``operationName=ProductList`` and copying the value out of the
# ``extensions.persistedQuery.sha256Hash`` query parameter.
AB_PRODUCTLIST_PERSISTED_HASH = (
    "1c53d86bec1b38b5767f39df2af0949e3bb90ce2a0afa177829d93cf26905800"
)

# AB returns 10 products per page in the live UI. Honour that — bumping
# the value tends to either silently cap or trigger their abuse guards.
AB_LAZY_LOAD_COUNT = 10

# Hard cap on pages crawled per run. The fixture's pagination block
# reported ``totalPages: 87`` on 2026-05-25; cap a touch higher to be
# tolerant of catalogue growth without crawling forever on a bug.
# Override per-environment with ``CRAWLER_MAX_PAGES_AB=<N>``.
AB_MAX_PAGES = max_pages_from_env("AB", default=120)


class AbSpider(scrapy.Spider):
    """Crawl active promotions on www.ab.gr via the storefront GraphQL API."""

    name = "ab"

    # Matches the seeded backend Brand.id for AB Vassilopoulos (slug "ab").
    # Same hard-coded MVP shortcut documented on the Lidl spider; the
    # pipeline will resolve via slug once we wire that up.
    brand_id = 1

    allowed_domains = ["ab.gr"]

    custom_settings = {
        # We're hitting a JSON API, not crawling HTML. robots.txt obey is
        # already on at project level; nothing more to add here, but keep
        # the delay generous because the GraphQL endpoint sits behind a
        # WAF that doesn't love bursts.
        "DOWNLOAD_DELAY": 2,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
    }

    # Coverage stats — populated as we walk pages, surfaced in
    # ``closed()`` so the run-log always carries an "X/Y pages reached"
    # audit line. Lets us spot the moment AB's catalogue starts
    # bumping against ``AB_MAX_PAGES``.
    _first_total_pages: int | None = None
    _last_page_reached: int = -1

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        # Per-family histogram — counts every product AB ships, whether
        # we emitted it or not. Surfaced in ``closed()`` so the run log
        # makes the spread visible without a DB dive.
        self._family_counts: Counter[str] = Counter()

    async def start(self):  # type: ignore[override]
        # Scrapy 2.13+ replaced ``start_requests`` with the async-iterable
        # ``start()``. We yield a single request for page 0; subsequent
        # pages are scheduled from ``parse`` as we discover them.
        yield self._build_page_request(page_number=0)

    # --- per-page ------------------------------------------------------------

    def parse(self, response: Response, **kwargs: Any) -> Any:  # type: ignore[override]
        page_number = response.meta.get("page_number", 0)

        try:
            payload = json.loads(response.text)
        except json.JSONDecodeError:
            logger.error(
                "ab: page {} returned non-JSON body (status {}); aborting spider",
                page_number,
                response.status,
            )
            return

        # GraphQL persisted-query miss arrives as {"errors":[{"message":
        # "PersistedQueryNotFound", ...}]} with no data block. Surface it
        # loudly so we know to refresh the hash.
        if not (payload.get("data") or {}).get("productList"):
            errors = payload.get("errors") or [{"message": "no data.productList"}]
            logger.error(
                "ab: empty productList on page {} — errors={}",
                page_number,
                errors,
            )
            return

        product_list = payload["data"]["productList"]
        pagination = product_list.get("pagination") or {}
        total_pages = int(pagination.get("totalPages") or 0)
        total_results = int(pagination.get("totalResults") or 0)

        # Audit trail: remember the first page's view of totalPages and
        # the highest page we've actually fetched. ``closed()`` logs the
        # delta so the operator can spot truncation at a glance.
        if self._first_total_pages is None:
            self._first_total_pages = total_pages
        self._last_page_reached = max(self._last_page_reached, page_number)

        scraped_at = datetime.now(UTC)
        emitted = 0
        page_families: Counter[str] = Counter()
        for family, offer in extract_offers_with_family(payload, scraped_at):
            page_families[family] += 1
            if offer is not None:
                emitted += 1
                yield offer
        self._family_counts.update(page_families)

        logger.info(
            "ab: page {}/{} yielded {} offers "
            "(of {} products in payload, {} total in catalogue) — page mix: {}",
            page_number,
            max(total_pages - 1, 0),
            emitted,
            len(product_list.get("products") or []),
            total_results,
            dict(page_families),
        )

        # Paginate. AB's pagination is 0-indexed; stop when we've covered
        # totalPages or hit our safety cap.
        next_page = page_number + 1
        if next_page >= total_pages:
            return
        if next_page >= AB_MAX_PAGES:
            logger.warning(
                "ab: hit AB_MAX_PAGES={} before totalPages={} — "
                "bump CRAWLER_MAX_PAGES_AB to crawl the full catalogue.",
                AB_MAX_PAGES,
                total_pages,
            )
            return
        yield self._build_page_request(page_number=next_page)

    def closed(self, reason: str) -> None:
        """Audit log: pages walked + per-family emit breakdown.

        Surfaces the promotion-family histogram so future runs make the
        spread visible without poking at the DB — exactly the question
        ("AB seems short — broken filter, or just no offers this week?")
        that motivated this spider's rewrite.
        """
        first_total = self._first_total_pages
        if first_total is None:
            logger.info("ab: closed without any successful page (reason={})", reason)
            return
        # ``_last_page_reached`` is the highest 0-indexed page; +1 for human count.
        pages_walked = self._last_page_reached + 1
        suffix = " (FULL COVERAGE)" if pages_walked >= first_total else " (TRUNCATED)"
        emitted_total = sum(v for k, v in self._family_counts.items() if k in EMITTED_FAMILIES)
        seen_total = sum(self._family_counts.values())
        logger.info(
            "ab: closed — walked {} of {} pages (cap {}, reason={}){}",
            pages_walked,
            first_total,
            AB_MAX_PAGES,
            reason,
            suffix,
        )
        logger.info(
            "ab: promo-family histogram (emitted={}, seen={}): {}",
            emitted_total,
            seen_total,
            dict(self._family_counts),
        )

    # --- helpers -------------------------------------------------------------

    def _build_page_request(self, *, page_number: int) -> scrapy.Request:
        """Construct the GET request for one page of the ProductList query.

        The variables block mirrors what the AB storefront sends; only
        ``pageNumber`` changes between pages.
        """
        variables = {
            "productListingType": "PROMOTION_SEARCH",
            "lang": "gr",
            "productCodes": "",
            "categoryCode": "",
            "excludedProductCodes": "",
            "brands": "",
            "keywords": "",
            "productTypes": "",
            "lazyLoadCount": AB_LAZY_LOAD_COUNT,
            "pageNumber": page_number,
            "sort": "",
            "searchQuery": "",
            "hideProductsWithoutPromo": False,
            "hideUnavailableProducts": True,
            "maxItemsToDisplay": 0,
            "includePotentialActivatableOffers": True,
        }
        extensions = {
            "persistedQuery": {
                "version": 1,
                "sha256Hash": AB_PRODUCTLIST_PERSISTED_HASH,
            }
        }
        params = {
            "operationName": "ProductList",
            "variables": json.dumps(variables, separators=(",", ":")),
            "extensions": json.dumps(extensions, separators=(",", ":")),
        }
        url = AB_GRAPHQL_URL + "?" + urlencode(params)
        return scrapy.Request(
            url=url,
            callback=self.parse,
            meta={"page_number": page_number},
            headers={
                # AB's WAF cares about Accept; mirror what the browser sends.
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "el-GR,el;q=0.9,en;q=0.7",
                "Referer": "https://www.ab.gr/search/promotions",
                # Apollo Server's CSRF-prevention middleware rejects GET
                # requests that don't either send a non-form Content-Type
                # *or* one of two opt-in headers. We use the documented
                # opt-in (``apollo-require-preflight``) — it forces a CORS
                # preflight on the browser path, which is exactly the
                # signal the server uses to mark the request "trusted".
                "apollo-require-preflight": "true",
                "x-apollo-operation-name": "ProductList",
            },
        )
