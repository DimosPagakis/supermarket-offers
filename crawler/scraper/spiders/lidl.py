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

Coverage audit (verified 2026-05-25)
------------------------------------
* Homepage advertises **all** active weekly campaigns — 31 unique
  ``/c/<theme>-{YY}kw{WW}/a{id}`` anchors when verified.
* ``/c/fylladio-lidl/s10020481`` (the "flyer landing" page) contains
  zero campaign anchors — it's an image-viewer shell. No additional
  URLs to discover there.
* ``https://www.lidl-hellas.gr/sitemap.xml`` does not exist
  (404). No XML sitemap to follow.
* Within a single campaign, **every** product is embedded in the
  same HTML response as ``data-grid-data="..."`` attributes —
  there is no "show more" trigger, lazy load, or sub-pagination on
  the listing. One HTTP GET per campaign covers the full set.

Conclusion: walking every homepage campaign anchor is the complete
"all available offers" discovery. There is no untapped URL bucket
on lidl-hellas.gr today.

Weekly offer-count variability (verified 2026-05-25 live run)
-------------------------------------------------------------
Lidl's *priced* offer count swings wildly between weeks and within a
week:

* Last-week campaigns (``...-26kw21``) keep their URLs alive for a
  day or two after Thursday rollover but ship cards with empty
  ``regionsPrices`` — those legitimately yield zero offers.
* Themed promo campaigns (``alpen-fest-style``, ``aroma-latinikis-
  amerikis``, ``paidi-axesoyar`` …) often render a hero banner with
  no priced products at all.
* The bulk of priced offers concentrate in 4–6 campaigns
  (``evdomadiaies-epiloges``, ``xxl-proionta``,
  ``parkside-performance``, ``silvercrest-koyzina``,
  ``ora-gia-psisimo``, ``lidl-plus``).

Live breakdown captured 2026-05-25 (kw22):

  cards  priced  campaign
   ----  ------  --------
     26      23  /c/evdomadiaies-epiloges-26kw22/a10095458
      8       6  /c/lidl-plus-26kw22/a10095457
      9       9  /c/ora-gia-psisimo-26kw22/a10095461
      5       5  /c/aparaitita-synodeytika-26kw22/a10095507
     12      12  /c/xxl-proionta-26kw22/a10095508
      4       4  /c/alpen-fest-style-26kw22/a10095509
      4       4  /c/aroma-latinikis-amerikis-26kw22/a10095510
      6       6  /c/apolaystiko-dialeimma-26kw22/a10095520
     11      11  /c/parkside-performance-ergaleia-exoplismos-26kw22/a10095521
      5       5  /c/paidi-paichnidi-26kw22/a10095522
      3       3  /c/paidi-endysi-26kw22/a10095529
      8       8  /c/silvercrest-koyzina-oikiakos-exoplismos-26kw22/a10095531
   (all other 19 campaigns yielded 0 priced offers — empty banners,
   expired kw21, or themed promos without priced cards)

  Total: 96 priced offers across 12 productive campaigns.

This is why we treat "zero priced offers on a campaign URL" as INFO
rather than WARNING — it's the modal outcome for ~60% of the campaign
anchors Lidl publishes.

Safety cap
----------
``LIDL_MAX_CAMPAIGNS`` puts a ceiling on how many campaign URLs we
follow per run. Defaults to a generous 200 — way above the 31
observed live — and is overridable via ``CRAWLER_MAX_PAGES_LIDL`` so
the scheduler can crank it without a code change.
"""

from __future__ import annotations

import re
from datetime import datetime, UTC
from typing import Any
from urllib.parse import urlparse

import scrapy
from loguru import logger
from scrapy.http import Response

from scraper.parsers.lidl import extract_offers
from scraper.spiders._config import max_pages_from_env

# Matches Lidl campaign URLs: /c/<theme>-{YY}kw{WW}/a{id}
# Examples:
#   /c/evdomadiaies-epiloges-26kw22/a10095458
#   /c/poiotita-poikilia-26kw21/a10095202
#   /c/parkside-ergaleia-exoplismos-26kw21/a10095190
_CAMPAIGN_HREF_RE = re.compile(r"^/c/[^/]+-\d{2}kw\d{1,2}/a\d+/?$")

# Safety cap on campaigns per run. Real catalogue sits well under 50.
# Override via ``CRAWLER_MAX_PAGES_LIDL=<N>`` if Lidl ever expands.
LIDL_MAX_CAMPAIGNS = max_pages_from_env("LIDL", default=200)


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
        # Collect every anchor matching the Lidl campaign URL shape, then
        # dedupe while preserving order — Lidl repeats the same campaign
        # in multiple homepage sections (hero, carousel, footer); we only
        # need to crawl each one once. ``dict.fromkeys`` preserves
        # insertion order in Python 3.7+.
        campaign_paths = (
            urlparse(href).path
            for href in response.css("a::attr(href)").getall()
            if href
        )
        ordered_unique = list(dict.fromkeys(
            p for p in campaign_paths if _CAMPAIGN_HREF_RE.match(p)
        ))

        if not ordered_unique:
            logger.warning(
                "lidl: no campaign anchors matched on homepage {} — "
                "selectors / URL pattern may be stale",
                response.url,
            )
            return

        if len(ordered_unique) > LIDL_MAX_CAMPAIGNS:
            logger.warning(
                "lidl: discovered {} campaign URLs, clipping to safety cap "
                "{} (bump CRAWLER_MAX_PAGES_LIDL to widen)",
                len(ordered_unique),
                LIDL_MAX_CAMPAIGNS,
            )
            ordered_unique = ordered_unique[:LIDL_MAX_CAMPAIGNS]

        logger.info(
            "lidl: discovered {} campaign URLs (cap {})",
            len(ordered_unique),
            LIDL_MAX_CAMPAIGNS,
        )

        for path in ordered_unique:
            yield scrapy.Request(
                url=response.urljoin(path),
                callback=self.parse_listing,
            )

    # --- Step 2: campaign listing -> OfferItems ------------------------------

    def parse_listing(self, response: Response) -> Any:
        scraped_at = datetime.now(UTC)
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
