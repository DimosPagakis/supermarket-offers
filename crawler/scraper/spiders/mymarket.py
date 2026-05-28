"""My Market offers-listing spider.

My Market server-side-renders ``/offers`` as a paginated HTML grid —
no JS required. Each page has 35 product cards (~161 pages = ~5600
catalogue items, of which the displayed prices are what shoppers see).

The catalogue on ``/offers`` mixes promoted SKUs with regular-shelf
SKUs. The parser gates emit on a real promo signal
(``span.diagonal-line`` strikethrough or ``.offer-note--percent``
pill) so only 1–9 cards per page yield. That's correct.

Pagination strategy
-------------------
The spider walks **every** page exposed by the storefront. On the
first page it reads the maximum ``data-mkey="page-N"`` anchor in the
pagination nav — that's the "go to last page" link a shopper would
click. Subsequent pages are scheduled in a tight chain until we hit
that total.

Empty-page tolerance
^^^^^^^^^^^^^^^^^^^^
Discount density is uneven across the catalogue — a given page can
yield 0 discounted offers and the next page still hold 4–6. The
original implementation stopped at the *first* zero-yield page,
which capped real coverage at the first dry-spell (incident
2026-05-25: full crawl reported 26 offers across 7 pages; live
sampling of pages 8–10 yielded 1–2 offers each, so the early-stop
was dropping ~90% of true coverage). We now tolerate
``MYMARKET_EMPTY_PAGE_RUN`` consecutive empty pages before giving
up — defaults to 8 so genuine selector drift still terminates a
run quickly, while normal discount sparsity doesn't.

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

# Safety cap. 161 known pages × 35 items ≈ 5600 catalogue items. The
# *actual* stop condition is the ``total_pages`` value the parser reads
# from page 1; this constant only kicks in if that detection breaks.
# Override per-environment with ``CRAWLER_MAX_PAGES_MYMARKET=<N>``.
MYMARKET_MAX_PAGES = max_pages_from_env("MYMARKET", default=300)

# How many consecutive zero-yield pages we tolerate before assuming
# the catalogue has been fully walked (or selectors have drifted) and
# bailing. See the module docstring for why this is 8 rather than 1.
MYMARKET_EMPTY_PAGE_RUN = 8


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
            meta={"page_number": 1, "empty_streak": 0},
        )

    def parse(self, response: Response, **kwargs: Any) -> Any:  # type: ignore[override]
        page_number = response.meta.get("page_number", 1)
        total_pages = response.meta.get("total_pages")
        empty_streak = response.meta.get("empty_streak", 0)

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
            empty_streak += 1
            logger.info(
                "my-market: page {}/{} yielded 0 discounted offers "
                "(empty_streak={}/{})",
                page_number,
                total_pages,
                empty_streak,
                MYMARKET_EMPTY_PAGE_RUN,
            )
            if empty_streak >= MYMARKET_EMPTY_PAGE_RUN:
                logger.warning(
                    "my-market: {} consecutive empty pages — stopping. "
                    "Either the catalogue tail has no more discounts or "
                    "selectors have drifted.",
                    empty_streak,
                )
                return
        else:
            logger.info(
                "my-market: page {}/{} yielded {} offers",
                page_number,
                total_pages,
                count,
            )
            empty_streak = 0

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
            meta={
                "page_number": next_page,
                "total_pages": total_pages,
                "empty_streak": empty_streak,
            },
        )
