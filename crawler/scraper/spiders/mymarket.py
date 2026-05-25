"""My Market offers-listing spider.

My Market server-side-renders ``/offers`` as a paginated HTML grid —
no JS required. Each page has 35 product cards (~158 pages = ~5500
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

To keep smoke-test runs snappy we cap pagination at ``MAX_PAGES``
pages. Bump that when we're ready to pay the full ~5min crawl.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import scrapy
from loguru import logger
from scrapy.http import Response

from scraper.parsers.mymarket import extract_offers

MYMARKET_OFFERS_URL = "https://www.mymarket.gr/offers"

# Safety cap. 158 known pages × 35 items ≈ 5500 catalogue items; raise
# this once we wire scheduling and can afford the full crawl in
# production. Default keeps an end-to-end smoke run under ~30 seconds.
MYMARKET_MAX_PAGES = 10


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
        scraped_at = datetime.now(timezone.utc)

        count = 0
        for offer in extract_offers(response.text, scraped_at):
            count += 1
            yield offer

        if count == 0:
            logger.warning(
                "my-market: zero cards parsed from {} — selectors / page "
                "structure may have changed",
                response.url,
            )
            return

        logger.info(
            "my-market: page {} yielded {} offers (cap {})",
            page_number,
            count,
            MYMARKET_MAX_PAGES,
        )

        next_page = page_number + 1
        if next_page > MYMARKET_MAX_PAGES:
            return

        yield scrapy.Request(
            url=f"{MYMARKET_OFFERS_URL}?page={next_page}",
            callback=self.parse,
            meta={"page_number": next_page},
        )
