"""AB Vassilopoulos promotion spider.

AB exposes a Next.js storefront whose product catalogue is fetched
client-side from a GraphQL persisted-query endpoint at
``https://www.ab.gr/api/v1/``. We bypass Playwright entirely — the
spider hits the GraphQL endpoint with the same operation, variables,
and sha256 hash the browser uses.

The heavy mapping logic lives in ``scraper.parsers.ab`` and is
exercised against a committed fixture so we'd catch a schema change
in plain pytest before a live run.

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
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlencode

import scrapy
from loguru import logger
from scrapy.http import Response

from scraper.parsers.ab import extract_offers_from_payload

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
AB_MAX_PAGES = 120


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

        scraped_at = datetime.now(timezone.utc)
        count = 0
        for offer in extract_offers_from_payload(payload, scraped_at):
            count += 1
            yield offer

        logger.info(
            "ab: page {}/{} yielded {} real-discount offers "
            "(of {} products in payload, {} total in catalogue)",
            page_number,
            max(total_pages - 1, 0),
            count,
            len(product_list.get("products") or []),
            total_results,
        )

        # Paginate. AB's pagination is 0-indexed; stop when we've covered
        # totalPages or hit our safety cap.
        next_page = page_number + 1
        if next_page >= min(total_pages, AB_MAX_PAGES):
            return
        yield self._build_page_request(page_number=next_page)

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
