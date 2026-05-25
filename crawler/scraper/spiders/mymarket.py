"""My Market offers-listing spider.

My Market server-side-renders ``/offers`` as a paginated HTML grid —
no JS required. Each page has 35 product cards (~159 pages = ~5500
catalogue items, of which the displayed prices are what shoppers see).

The catalogue on ``/offers`` includes both items currently on
promotion and items at their regular price (the listing isn't strict
about that distinction). For the MVP we emit every card as an offer
record; refining to only-discounted will need either:
  * a separate badge / strikethrough detector we haven't seen yet, or
  * an API endpoint that exposes a discount flag.

Either way, the listing view doesn't lie about the displayed price,
which is what a shopper would pay today — that's the right thing to
record for an aggregator.

Pagination strategy
-------------------
The spider walks **every** page exposed by the storefront. On the
first page it reads the maximum ``data-mkey="page-N"`` anchor in the
pagination nav — that's the "go to last page" link a shopper would
click. Subsequent pages are scheduled in a tight chain until we hit
that total. As a defence-in-depth fallback, the spider also stops if
a page returns zero ``.product--teaser`` cards (selector drift or
catalogue truncation).

``MYMARKET_MAX_PAGES`` is a hard safety cap that protects us from a
parser bug ever scheduling thousands of requests. It is **not** the
expected stop condition — the dynamic ``total_pages`` from the HTML
is. Bump the env override ``CRAWLER_MAX_PAGES_MYMARKET`` if My Market
ever exceeds the cap; the spider will warn on the run log when the
cap clips real coverage.
"""

from __future__ import annotations

from datetime import datetime, UTC
from typing import Any

import scrapy
from loguru import logger
from scrapy.http import Response

from scraper.parsers.mymarket import extract_offers, extract_total_pages
from scraper.spiders._config import max_pages_from_env

MYMARKET_OFFERS_URL = "https://www.mymarket.gr/offers"

# Safety cap. 159 known pages × 35 items ≈ 5500 catalogue items. The
# *actual* stop condition is the ``total_pages`` value the parser reads
# from page 1; this constant only kicks in if that detection breaks.
# Override per-environment with ``CRAWLER_MAX_PAGES_MYMARKET=<N>``.
MYMARKET_MAX_PAGES = max_pages_from_env("MYMARKET", default=300)


class MyMarketSpider(scrapy.Spider):
    """Crawl ``/offers`` listing pages and yield one OfferItem per card."""

    name = "my-market"

    # Matches the seeded backend Brand.id for My Market (slug "my-market").
    brand_id = 4

    allowed_domains = ["mymarket.gr"]

    custom_settings = {
        # Static HTML, no JS needed. Be polite — My Market doesn't
        # advertise scraping limits but a 2s delay keeps us well within
        # "ordinary browser" load.
        "DOWNLOAD_DELAY": 2,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 2,
    }

    async def start(self):  # type: ignore[override]
        # ``/offers`` itself is page 1. Subsequent pages use ``?page=N``.
        yield scrapy.Request(
            url=MYMARKET_OFFERS_URL,
            callback=self.parse,
            meta={"page_number": 1},
        )

    def parse(self, response: Response, **kwargs: Any) -> Any:  # type: ignore[override]
        page_number = response.meta.get("page_number", 1)
        total_pages = response.meta.get("total_pages")

        # Only the first page is asked for ``total_pages``; cache it on
        # subsequent requests so we don't re-parse the pagination block.
        if total_pages is None:
            total_pages = extract_total_pages(response.text)
            if total_pages is None:
                # No pagination at all — treat as a single-page listing.
                total_pages = 1
            else:
                logger.info(
                    "my-market: detected total_pages={} (safety cap {})",
                    total_pages,
                    MYMARKET_MAX_PAGES,
                )
                if total_pages > MYMARKET_MAX_PAGES:
                    logger.warning(
                        "my-market: total_pages={} exceeds safety cap {}; "
                        "the crawl will stop early. Bump "
                        "CRAWLER_MAX_PAGES_MYMARKET to crawl the full catalogue.",
                        total_pages,
                        MYMARKET_MAX_PAGES,
                    )

        scraped_at = datetime.now(UTC)

        count = 0
        for offer in extract_offers(response.text, scraped_at):
            count += 1
            yield offer

        if count == 0:
            logger.warning(
                "my-market: zero cards parsed from {} — selectors / page "
                "structure may have changed (stopping pagination)",
                response.url,
            )
            return

        logger.info(
            "my-market: page {}/{} yielded {} offers",
            page_number,
            total_pages,
            count,
        )

        next_page = page_number + 1
        effective_max = min(total_pages, MYMARKET_MAX_PAGES)
        if next_page > effective_max:
            logger.info(
                "my-market: crawl complete — walked pages 1..{} (total_pages={})",
                page_number,
                total_pages,
            )
            return

        yield scrapy.Request(
            url=f"{MYMARKET_OFFERS_URL}?page={next_page}",
            callback=self.parse,
            meta={"page_number": next_page, "total_pages": total_pages},
        )
