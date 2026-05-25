"""Lidl Hellas flyer spider — skeleton.

Strategy
--------
1. Start at https://www.lidl-hellas.gr/c/fylladio-lidl/s10020481 — the
   landing page that lists the current weekly flyers (food/non-food).
2. Find anchors that look like a flyer block. Lidl labels these with
   the Greek word "Από" (= "From") followed by the start date. We pick
   the first link we find — this is the most-recent flyer on the page.
3. Follow that link and parse offers from the flyer detail page.

This is intentionally written defensively. Lidl's markup changes
frequently and we don't have a stable HTML fixture yet, so:
  - If CSS selectors miss, the spider logs a clear warning and yields
    nothing rather than crashing.
  - Next iteration: capture real HTML, tune selectors, add fixtures.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import scrapy
from loguru import logger
from scrapy.http import Response

from scraper.items import OfferItem
from scraper.normalize import (
    clean_text,
    parse_date_range,
    parse_discount_pct,
    parse_price,
)


class LidlSpider(scrapy.Spider):
    """Crawl the current weekly flyer on lidl-hellas.gr."""

    name = "lidl"
    brand_id = 1  # matches backend Brand.id for Lidl; adjust once seeded.

    allowed_domains = ["lidl-hellas.gr"]
    start_urls = ["https://www.lidl-hellas.gr/c/fylladio-lidl/s10020481"]

    custom_settings = {
        # Lidl pages are mostly static HTML; no Playwright needed here.
        "DOWNLOAD_DELAY": 2,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 2,
    }

    # --- Step 1: landing page -> find current flyer link -----------------------

    def parse(self, response: Response, **_: Any) -> Any:
        # Candidate anchors: any link whose surrounding text mentions "Από"
        # (Greek for "From") — Lidl uses this as the validity-period label.
        candidate_links = response.xpath(
            "//a[.//text()[contains(., 'Από')] or "
            "contains(translate(@aria-label,'ΑΠΟ','απο'),'απο')]"
            "/@href"
        ).getall()

        # Fallback: any anchor pointing into the flyer subpath.
        if not candidate_links:
            candidate_links = response.css(
                "a[href*='/c/fylladio'], a[href*='/p/fylladio']"
            ).xpath("@href").getall()

        if not candidate_links:
            logger.warning(
                "lidl: no flyer link found on landing page {} — selectors likely stale",
                response.url,
            )
            return

        flyer_url = response.urljoin(candidate_links[0])
        logger.info("lidl: following flyer {}", flyer_url)

        yield scrapy.Request(
            url=flyer_url,
            callback=self.parse_flyer,
            cb_kwargs={"flyer_url": flyer_url},
        )

    # --- Step 2: flyer detail page -> yield offers -----------------------------

    def parse_flyer(self, response: Response, flyer_url: str) -> Any:
        # Look for a header / banner that contains the validity range.
        header_text = " ".join(
            response.css(
                "h1::text, h2::text, .flyer-header *::text, "
                "[class*='valid'] *::text, [class*='date'] *::text"
            ).getall()
        )
        valid_from, valid_to = parse_date_range(header_text)
        if not (valid_from or valid_to):
            logger.warning(
                "lidl: could not parse flyer validity dates from header on {} "
                "— header_text={!r}",
                flyer_url,
                header_text[:200],
            )

        # Offer cards. Lidl historically uses elements like
        # `.product-grid-box`, `.ret-o-product-tile`, `[class*='product-tile']`,
        # but the markup is unstable. Try several known patterns.
        cards = response.css(
            ".product-grid-box, .ret-o-product-tile, "
            "[class*='product-tile'], [class*='ProductCard']"
        )

        if not cards:
            logger.warning(
                "lidl: no product cards matched on {} — selectors likely stale",
                flyer_url,
            )
            return

        scraped_at = datetime.now(timezone.utc)
        count = 0
        for card in cards:
            offer = self._extract_offer(
                card=card,
                base_url=response.url,
                valid_from=valid_from,
                valid_to=valid_to,
                scraped_at=scraped_at,
            )
            if offer is not None:
                count += 1
                yield offer

        logger.info("lidl: yielded {} offers from {}", count, flyer_url)

    # --- Helpers ---------------------------------------------------------------

    def _extract_offer(
        self,
        *,
        card: Any,
        base_url: str,
        valid_from: Any,
        valid_to: Any,
        scraped_at: datetime,
    ) -> OfferItem | None:
        try:
            name = clean_text(
                " ".join(
                    card.css(
                        "h3::text, h4::text, "
                        "[class*='title']::text, [class*='name']::text"
                    ).getall()
                )
            )
            if not name:
                return None

            price_text = " ".join(
                card.css(
                    "[class*='price']::text, [class*='Price']::text"
                ).getall()
            )
            price = parse_price(price_text)
            if price is None:
                return None

            original_text = " ".join(
                card.css(
                    "[class*='strike']::text, [class*='old']::text, "
                    "[class*='was']::text, del::text, s::text"
                ).getall()
            )
            original_price = parse_price(original_text)

            discount_text = " ".join(
                card.css(
                    "[class*='discount']::text, [class*='badge']::text, "
                    "[class*='save']::text"
                ).getall()
            )
            discount_pct = parse_discount_pct(discount_text)

            image_url = card.css(
                "img::attr(src), img::attr(data-src), source::attr(srcset)"
            ).get()
            if image_url:
                # Take first url from srcset if applicable.
                image_url = image_url.split(",")[0].strip().split(" ")[0]

            href = card.css("a::attr(href)").get()
            offer_url = self._urljoin(base_url, href) if href else None

            external_id = card.css(
                "::attr(data-product-id), ::attr(data-id), ::attr(id)"
            ).get()

            unit = clean_text(
                " ".join(
                    card.css(
                        "[class*='unit']::text, [class*='package']::text, "
                        "[class*='weight']::text"
                    ).getall()
                )
            )

            return OfferItem(
                external_id=clean_text(external_id),
                name=name,
                url=offer_url,
                image_url=image_url,
                category=None,
                unit=unit,
                price=price,
                original_price=original_price,
                discount_pct=discount_pct,
                currency="EUR",
                valid_from=valid_from,
                valid_to=valid_to,
                scraped_at=scraped_at,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("lidl: failed to extract offer from card: {}", exc)
            return None

    @staticmethod
    def _urljoin(base: str, href: str) -> str:
        from urllib.parse import urljoin

        return urljoin(base, href)
