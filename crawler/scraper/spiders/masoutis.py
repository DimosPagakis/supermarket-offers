"""Masoutis promotional-items spider.

Masoutis ships its promo catalogue from a signed JSON endpoint that
requires three request headers (``uid``, ``usl``, ``key``) computed
client-side from a secret. We sidestep the signing problem by
driving Playwright once to load the promotions page; the browser's
JS computes the signed headers and fires the API request. We listen
for the response and pull the JSON straight off the wire.

Trade-offs vs. AB's pure-HTTP approach:
  * +1 minute per run for the Playwright bootstrap (vs ~3 minutes
    paginating AB's GraphQL, so net wash).
  * No persisted-query-hash brittleness because we replay nothing.
  * Loses the ability to scale concurrency on Masoutis without
    spinning multiple browsers. The promo list is only ~50 items, so
    that's a non-problem for the MVP.

The heavy mapping logic lives in ``scraper.parsers.masoutis`` and is
unit-tested against a committed fixture. This spider is the I/O
shell.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

import scrapy
from loguru import logger

from scraper.parsers.masoutis import extract_offers

MASOUTIS_PROMOS_URL = (
    "https://www.masoutis.gr/categories/index/prosfores?item=0"
)
MASOUTIS_PROMO_API_FRAGMENT = "GetPromoItemWithListCouponsSubCategoriesAutoPromos"


class MasoutisSpider(scrapy.Spider):
    """Yield OfferItems for the Masoutis offers page via a Playwright bootstrap."""

    name = "masoutis"

    # Matches the seeded backend Brand.id for Masoutis (slug "masoutis").
    brand_id = 5

    allowed_domains = ["masoutis.gr"]

    custom_settings = {
        # We don't go to network from Scrapy itself; the bootstrap is
        # entirely Playwright-driven. Keep the engine quiet.
        "DOWNLOAD_DELAY": 0,
        "CONCURRENT_REQUESTS": 1,
    }

    async def start(self):  # type: ignore[override]
        """Bootstrap via Playwright, yield OfferItems straight to the pipeline.

        Scrapy 2.13+ ``start()`` can yield items in addition to Requests,
        which is what we exploit here — the spider has no HTTP fetching
        of its own, the catalogue arrives via the bootstrap browser.
        """
        payload_text = await self._fetch_promo_payload()
        if not payload_text:
            logger.error(
                "masoutis: bootstrap failed — no promo payload captured. "
                "Site may have changed or Playwright blocked."
            )
            return

        scraped_at = datetime.now(timezone.utc)
        count = 0
        for offer in extract_offers(payload_text, scraped_at):
            count += 1
            yield offer

        logger.info("masoutis: yielded {} offers from bootstrap payload", count)

    # --- helpers -------------------------------------------------------------

    async def _fetch_promo_payload(self) -> str | None:
        """Drive a headless Chromium to the promos page and intercept the
        signed promo-API response. Returns the raw JSON body or None.
        """
        # Imported lazily so spiders that don't need Playwright don't pay
        # the import cost.
        from playwright.async_api import async_playwright

        captured: dict[str, str] = {}

        async def on_response(resp: Any) -> None:
            # We listen for the v2 endpoint and grab the first 200 response;
            # the page fires it exactly once per load.
            if MASOUTIS_PROMO_API_FRAGMENT in resp.url and resp.status == 200:
                try:
                    captured["body"] = await resp.text()
                except Exception as exc:  # noqa: BLE001
                    logger.warning("masoutis: failed to read response body: {}", exc)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            try:
                ctx = await browser.new_context(
                    locale="el-GR",
                    user_agent=(
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/130.0.0.0 Safari/537.36"
                    ),
                )
                page = await ctx.new_page()
                page.on("response", on_response)
                try:
                    await page.goto(MASOUTIS_PROMOS_URL, timeout=90_000)
                except Exception as exc:  # noqa: BLE001
                    logger.error("masoutis: page.goto failed: {}", exc)

                # The promo API is fired during initial hydration. Poll up to
                # 30s for the response to arrive on the network listener.
                for _ in range(15):
                    if "body" in captured:
                        break
                    await page.wait_for_timeout(2000)
            finally:
                await browser.close()

        return captured.get("body")
