"""Masoutis promotional-items spider.

Masoutis ships its promo catalogue from a signed JSON endpoint that
requires three request headers (``uid``, ``usl``, ``key``) computed
client-side from a secret. We sidestep the signing problem by
driving Playwright once to load the promotions page; the browser's
JS computes the signed headers and fires the API request. We listen
for the first response, **capture the signed headers off the wire**,
then replay them ourselves from the page's request context to fetch
every subsequent page — same auth, no scroll-to-load gymnastics.

Pagination strategy
-------------------
The Masoutis storefront paginates the same signed endpoint
(``POST /api/eshop/GetPromoItemWithListCouponsSubCategoriesAutoPromosv2``)
via the ``IfWeight`` body field — ``"1"`` is page 1, ``"2"`` is page 2,
and so on. Each page returns 50 items; the final page returns < 50.
The 2026-05-25 catalogue was 62 pages = ~3000 items.

We stop when:
  * a response carries fewer than ``PAGE_SIZE_HINT`` items (final page), or
  * a response is an empty list (defensive: never observed), or
  * we hit the ``MASOUTIS_MAX_PAGES`` safety cap.

Override the cap with ``CRAWLER_MAX_PAGES_MASOUTIS=<N>``.

Trade-offs vs. AB's pure-HTTP approach:
  * Still +1 minute per run for the Playwright bootstrap.
  * No persisted-query-hash brittleness because we replay nothing
    *across runs* — fresh signed headers every crawl.
  * Concurrency is irrelevant: one browser, one page, sequential
    page-fetches inside that page's request context.

The heavy mapping logic lives in ``scraper.parsers.masoutis`` and is
unit-tested against a committed fixture. This spider is the I/O
shell.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, UTC
from typing import Any

import scrapy
from loguru import logger

from scraper.parsers.masoutis import extract_offers_from_payload

MASOUTIS_BASE_URL = "https://www.masoutis.gr"
MASOUTIS_PROMOS_URL = (
    f"{MASOUTIS_BASE_URL}/categories/index/prosfores?item=0"
)
MASOUTIS_PROMO_API_PATH = (
    "/api/eshop/GetPromoItemWithListCouponsSubCategoriesAutoPromosv2"
)
MASOUTIS_PROMO_API_URL = MASOUTIS_BASE_URL + MASOUTIS_PROMO_API_PATH

# Page size as observed on 2026-05-25. The endpoint doesn't accept a
# page-size parameter; this is informational, used purely as the
# "final page detector" threshold.
PAGE_SIZE_HINT = 50

# Safety cap. 62 known pages × 50 items ≈ 3000 catalogue items.
# Override with ``CRAWLER_MAX_PAGES_MASOUTIS=<N>``.
MASOUTIS_MAX_PAGES = int(os.getenv("CRAWLER_MAX_PAGES_MASOUTIS", "300"))


class MasoutisSpider(scrapy.Spider):
    """Yield OfferItems for the full Masoutis offers catalogue via Playwright."""

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
        scraped_at = datetime.now(UTC)
        total_pages_seen = 0
        total_items = 0

        async for page_items in self._iter_promo_pages():
            total_pages_seen += 1
            page_count = 0
            for offer in extract_offers_from_payload(page_items, scraped_at):
                page_count += 1
                total_items += 1
                yield offer
            logger.info(
                "masoutis: page {} yielded {} offers ({} raw items)",
                total_pages_seen,
                page_count,
                len(page_items) if isinstance(page_items, list) else 0,
            )

        if total_pages_seen == 0:
            logger.error(
                "masoutis: bootstrap failed — no promo payload captured. "
                "Site may have changed or Playwright blocked."
            )
        else:
            logger.info(
                "masoutis: crawl complete — {} pages, {} offers (safety cap {})",
                total_pages_seen,
                total_items,
                MASOUTIS_MAX_PAGES,
            )

    # --- helpers -------------------------------------------------------------

    async def _iter_promo_pages(self):
        """Async-iterate the full paginated promo API.

        Drives a single headless Chromium session: loads the promo page
        (so JS computes the signed ``uid``/``usl``/``key`` headers),
        captures those headers off the first request, then replays the
        same POST with incrementing ``IfWeight`` until the catalogue
        runs out.
        """
        from playwright.async_api import async_playwright

        captured_headers: dict[str, str] = {}
        captured_first_body: dict[str, Any] = {}

        def _header_filter(headers: dict[str, str]) -> dict[str, str]:
            # We only need the auth trio + content-type; the rest of the
            # browser headers are noise and some (``host``,
            # ``content-length``) cannot legally be set by user JS.
            wanted = {"uid", "usl", "key", "content-type"}
            return {
                k: v for k, v in headers.items() if k.lower() in wanted
            }

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

                async def on_request(req: Any) -> None:
                    if (
                        MASOUTIS_PROMO_API_PATH in req.url
                        and not captured_headers
                    ):
                        try:
                            captured_headers.update(
                                _header_filter(await req.all_headers())
                            )
                        except Exception as exc:  # noqa: BLE001
                            logger.warning(
                                "masoutis: failed to capture headers: {}", exc
                            )

                async def on_response(resp: Any) -> None:
                    if (
                        MASOUTIS_PROMO_API_PATH in resp.url
                        and resp.status == 200
                        and not captured_first_body
                    ):
                        try:
                            body_text = await resp.text()
                            parsed = json.loads(body_text)
                            if isinstance(parsed, list):
                                captured_first_body["data"] = parsed
                        except Exception as exc:  # noqa: BLE001
                            logger.warning(
                                "masoutis: failed to read first body: {}", exc
                            )

                page.on("request", on_request)
                page.on("response", on_response)

                try:
                    await page.goto(MASOUTIS_PROMOS_URL, timeout=90_000)
                except Exception as exc:  # noqa: BLE001
                    logger.error("masoutis: page.goto failed: {}", exc)
                    return

                # Wait up to 30s for the bootstrap signed call to land.
                for _ in range(15):
                    if captured_first_body and captured_headers:
                        break
                    await page.wait_for_timeout(2000)

                if not captured_first_body:
                    logger.error(
                        "masoutis: no initial promo response captured — "
                        "site may have changed."
                    )
                    return
                if not captured_headers:
                    logger.error(
                        "masoutis: captured first response but no signed "
                        "headers — pagination is impossible without them."
                    )
                    # Still yield page 1, give the operator something.
                    yield captured_first_body["data"]
                    return

                # Page 1 is already on the wire — yield it.
                yield captured_first_body["data"]

                page1_count = len(captured_first_body["data"])
                if page1_count < PAGE_SIZE_HINT:
                    # Either the catalogue shrank below one page, or
                    # PAGE_SIZE_HINT is stale. Either way, we're done.
                    return

                # Pages 2..N: replay the signed POST from this page's
                # request context. ``page.request`` shares the browser
                # session (cookies + origin), so the storefront's CSRF
                # and rate-limit signals stay consistent.
                for page_number in range(2, MASOUTIS_MAX_PAGES + 1):
                    body = {
                        "PassKey": "Sc@NnSh0p",
                        "Itemcode": "0",
                        "ItemDescr": "2",
                        "IfWeight": str(page_number),
                        "ServiceResponse": "",
                        "Token": "",
                        "Zip": "",
                        "BrandName": "",
                        "TeamId": "",
                        "ExtraFilter": "",
                    }
                    try:
                        api_resp = await page.request.post(
                            MASOUTIS_PROMO_API_URL,
                            headers=captured_headers,
                            data=json.dumps(body),
                            timeout=30_000,
                        )
                    except Exception as exc:  # noqa: BLE001
                        logger.error(
                            "masoutis: page {} request failed: {}",
                            page_number,
                            exc,
                        )
                        return

                    if api_resp.status != 200:
                        logger.error(
                            "masoutis: page {} returned HTTP {} — stopping",
                            page_number,
                            api_resp.status,
                        )
                        return

                    try:
                        body_text = await api_resp.text()
                        page_data = json.loads(body_text)
                    except Exception as exc:  # noqa: BLE001
                        logger.error(
                            "masoutis: page {} body decode failed: {}",
                            page_number,
                            exc,
                        )
                        return

                    if not isinstance(page_data, list):
                        logger.warning(
                            "masoutis: page {} returned non-list payload "
                            "(type={}); stopping",
                            page_number,
                            type(page_data).__name__,
                        )
                        return

                    yield page_data

                    if len(page_data) < PAGE_SIZE_HINT:
                        # Last page — fewer than a full batch.
                        return

                else:  # for-else: ran to the end of range without breaking
                    logger.warning(
                        "masoutis: hit MASOUTIS_MAX_PAGES={} — bump "
                        "CRAWLER_MAX_PAGES_MASOUTIS if the real catalogue "
                        "is larger.",
                        MASOUTIS_MAX_PAGES,
                    )
            finally:
                await browser.close()
