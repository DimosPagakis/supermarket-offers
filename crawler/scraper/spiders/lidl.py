"""Lidl Hellas weekly-offer spider.

Strategy (revised — see ``crawler/tests/fixtures/lidl/listing.html``)
--------------------------------------------------------------------
1. Start at the homepage (``https://www.lidl-hellas.gr/``) — the most
   stable URL on the site.
2. The homepage lists every active campaign as ``<a href="/c/<theme>-
   {YY}kw{WW}/a{id}">`` anchors (e.g.
   ``/c/evdomadiaies-epiloges-26kw22/a10095458``). The slug rotates
   weekly, so we discover URLs dynamically rather than seeding them.
3. Each campaign URL renders a real HTML listing page that embeds
   every product as ``data-grid-data="<HTML-entity-encoded JSON>"``.
   The heavy lifting (decoding the JSON, mapping it to ``OfferItem``)
   lives in ``scraper.parsers.lidl`` so the same logic can be exercised
   in plain pytest against the committed fixture.

This replaces the earlier flyer-based approach, which followed
``/c/fylladio-lidl/...`` and ended up on an image-viewer page with no
parseable product HTML. The campaign pages above contain the same
products in structured JSON.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import scrapy
from loguru import logger
from scrapy.http import Response

from scraper.parsers.lidl import extract_offers

# Matches Lidl campaign URLs: /c/<theme>-{YY}kw{WW}/a{id}
# Examples:
#   /c/evdomadiaies-epiloges-26kw22/a10095458
#   /c/poiotita-poikilia-26kw21/a10095202
#   /c/parkside-ergaleia-exoplismos-26kw21/a10095190
_CAMPAIGN_HREF_RE = re.compile(r"^/c/[^/]+-\d{2}kw\d{1,2}/a\d+/?$")


class LidlSpider(scrapy.Spider):
    """Crawl every active weekly campaign on lidl-hellas.gr."""

    name = "lidl"

    # Matches the seeded backend Brand.id for Lidl (slug "lidl"). Hard-coded
    # for the MVP smoke test; a future iteration will resolve brand_id by
    # hitting GET /api/v1/brands and matching on the spider name/slug.
    brand_id = 3

    allowed_domains = ["lidl-hellas.gr"]
    start_urls = ["https://www.lidl-hellas.gr/"]

    custom_settings = {
        # Static HTML listings; no Playwright needed.
        "DOWNLOAD_DELAY": 2,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 2,
    }

    # --- Step 1: homepage -> active campaign URLs ----------------------------

    def parse(self, response: Response, **_: Any) -> Any:
        # Collect every anchor that matches the Lidl campaign URL shape.
        hrefs = response.css("a::attr(href)").getall()
        campaign_paths: list[str] = []
        for raw in hrefs:
            if not raw:
                continue
            parsed = urlparse(raw)
            path = parsed.path
            if _CAMPAIGN_HREF_RE.match(path):
                campaign_paths.append(path)

        # Dedupe while preserving order. Lidl repeats the same campaign in
        # multiple homepage sections (hero, carousel, footer); we only need
        # to crawl each one once.
        seen: set[str] = set()
        ordered_unique: list[str] = []
        for path in campaign_paths:
            if path not in seen:
                seen.add(path)
                ordered_unique.append(path)

        if not ordered_unique:
            logger.warning(
                "lidl: no campaign anchors matched on homepage {} — "
                "selectors / URL pattern may be stale",
                response.url,
            )
            return

        logger.info("lidl: discovered {} campaign URLs", len(ordered_unique))

        for path in ordered_unique:
            yield scrapy.Request(
                url=response.urljoin(path),
                callback=self.parse_listing,
            )

    # --- Step 2: campaign listing -> OfferItems ------------------------------

    def parse_listing(self, response: Response) -> Any:
        scraped_at = datetime.now(timezone.utc)
        count = 0
        for offer in extract_offers(response.text, scraped_at):
            count += 1
            yield offer

        if count == 0:
            # Two reasons this can legitimately fire:
            #  1. Old-week / expired campaign pages: the page still exists
            #     and embeds product cards, but none carry a current price
            #     block (regionsPrices empty or futurePrices == []). This
            #     is normal — Lidl keeps last week's URLs alive briefly.
            #  2. Genuine selector / schema drift — the page has product
            #     cards but the parser didn't recognise them.
            # The parser logs a DEBUG line with the data-grid-data count so
            # the operator can tell the two apart in the run log.
            logger.info(
                "lidl: zero priced offers on {} — probably an expired "
                "campaign; inspect the parser DEBUG line if unexpected",
                response.url,
            )
        else:
            logger.info("lidl: yielded {} offers from {}", count, response.url)
