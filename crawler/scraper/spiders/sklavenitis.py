"""Sklavenitis offers-listing spider.

Sklavenitis sits behind Akamai Bot Manager: any HTTP client with a
non-Chrome TLS handshake (curl/LibreSSL, ``httpx``, Scrapy's
``urllib3``-based downloader, etc.) gets ``403 Access Denied`` at the
edge before a single byte of HTML is served. Stealthed headless
Playwright is overkill for a static HTML listing; the lightest
solution that actually works is ``curl_cffi``, which forwards the
request through libcurl-impersonate so the JA3 fingerprint matches
real Chrome.

We therefore bypass Scrapy's downloader entirely:

* ``async def start()`` (Scrapy 2.13+) fetches every page with
  ``curl_cffi.requests.AsyncSession(impersonate="chrome131")``,
* parses the HTML with the pure-function parser in
  ``scraper.parsers.sklavenitis``, and
* yields ``OfferItem`` instances straight into the pipeline.

A safety cap (``SKLAVENITIS_MAX_PAGES``) keeps smoke runs short — the
full catalogue is ~2,988 items across ~125 pages and takes ≈ 8
minutes at the polite 3 s delay. Bump the cap when scheduling is
real.

Trade-offs vs. a Playwright bootstrap:
  * +much faster (no Chromium spawn, plain HTTP).
  * −no JS-side hydration; we only see what the server renders, but
    the listing is server-rendered so that's all we need.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, UTC

import scrapy
from loguru import logger

from scraper.parsers.sklavenitis import extract_offers
from scraper.spiders._config import max_pages_from_env

SKLAVENITIS_BASE_URL = "https://www.sklavenitis.gr"
SKLAVENITIS_OFFERS_PATH = "/sylloges/prosfores/"

# Safety cap. ~125 known pages × 24 cards ≈ 3,000 catalogue items; the
# default is set high enough to cover the full catalogue with headroom.
# Override at runtime with ``CRAWLER_MAX_PAGES_SKLAVENITIS=<N>`` (e.g.
# drop to 5 for a fast smoke run, raise if Sklavenitis grows their
# catalogue past ~7000 items).
SKLAVENITIS_MAX_PAGES = max_pages_from_env("SKLAVENITIS", default=300)

# Akamai-friendly: behave like a real browser tab opened from the
# homepage. Anything more aggressive risks waking the WAF.
SKLAVENITIS_REQUEST_DELAY_S = 3.0

# Chrome impersonation profile. curl_cffi maps this to a libcurl-
# impersonate target with the matching JA3 / HTTP2 fingerprint.
SKLAVENITIS_IMPERSONATE = "chrome131"


class SklavenitisSpider(scrapy.Spider):
    """Yield OfferItems for Sklavenitis ``/sylloges/prosfores`` listings.

    DEFERRED (2026-05-25): the brand is seeded ``active=false``. The
    configured ``/sylloges/prosfores`` URL is misnamed — it ships the
    chain's full active catalogue with no per-card discount markup
    (no strikethrough, no original price, no "-N%" pill). The lone
    observable per-card promo signal is a ``.sign-badges`` "N+M Δώρο"
    gift badge present on ~1 in 24 cards. Under the discounted-only
    emit policy the parser keeps only those cards — a fair correctness
    win but far too narrow a yield to justify activating the spider.
    Re-activate this brand (in ``BrandSeeder``) once a real flyer
    entry point is identified or Sklavenitis adds strikethrough markup
    to its listing.
    """

    name = "sklavenitis"

    # Matches the seeded backend Brand.id for Sklavenitis (slug "sklavenitis").
    brand_id = 2

    allowed_domains = ["sklavenitis.gr"]

    custom_settings = {
        # We don't go to network via Scrapy's downloader — fetches happen
        # inside ``start()`` with curl_cffi. Keep the engine quiet.
        "DOWNLOAD_DELAY": 0,
        "CONCURRENT_REQUESTS": 1,
        # We obey robots.txt for other brands; Sklavenitis' robots.txt is
        # also Akamai-gated so Scrapy's check would 403 even without us
        # touching it. Disable for this spider only — the actual fetch
        # path is polite (3 s delay, single thread).
        "ROBOTSTXT_OBEY": False,
    }

    async def start(self):  # type: ignore[override]
        """Fetch listing pages via curl_cffi and yield OfferItems."""
        # Import locally so the optional dep only loads for this spider.
        try:
            from curl_cffi.requests import AsyncSession
        except ImportError as exc:  # pragma: no cover - defensive
            logger.error(
                "sklavenitis: curl_cffi not installed ({}). "
                "Run `pip install curl_cffi`.",
                exc,
            )
            return

        scraped_at = datetime.now(UTC)
        total = 0

        async with AsyncSession(impersonate=SKLAVENITIS_IMPERSONATE) as session:
            # Warm-up: hit the homepage once to acquire the AKA_A2 cookie
            # Akamai sets. Empirically the offers page works without it
            # too, but the warm-up matches what a real browser would do
            # and gives us cookies for any follow-up requests.
            try:
                home = await session.get(
                    SKLAVENITIS_BASE_URL + "/",
                    headers=_base_headers(referer=None),
                    timeout=30,
                )
                logger.info(
                    "sklavenitis: warm-up GET / -> {} ({} bytes)",
                    home.status_code,
                    len(home.text),
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("sklavenitis: warm-up failed: {}", exc)

            for page_number in range(1, SKLAVENITIS_MAX_PAGES + 1):
                url = _page_url(page_number)
                referer = (
                    SKLAVENITIS_BASE_URL + SKLAVENITIS_OFFERS_PATH
                    if page_number > 1
                    else SKLAVENITIS_BASE_URL + "/"
                )
                try:
                    resp = await session.get(
                        url,
                        headers=_base_headers(referer=referer),
                        timeout=30,
                    )
                except Exception as exc:  # noqa: BLE001
                    logger.error(
                        "sklavenitis: page {} fetch failed: {}", page_number, exc
                    )
                    break

                if resp.status_code != 200:
                    logger.error(
                        "sklavenitis: page {} returned {} — aborting "
                        "(Akamai may have rotated us; rerun later)",
                        page_number,
                        resp.status_code,
                    )
                    break

                page_count = 0
                for offer in extract_offers(resp.text, scraped_at):
                    page_count += 1
                    yield offer

                total += page_count
                logger.info(
                    "sklavenitis: page {} yielded {} offers (cumulative {})",
                    page_number,
                    page_count,
                    total,
                )

                if page_count == 0:
                    logger.warning(
                        "sklavenitis: page {} parsed zero cards — selectors "
                        "or page structure may have changed, stopping early",
                        page_number,
                    )
                    break

                if page_number < SKLAVENITIS_MAX_PAGES:
                    await asyncio.sleep(SKLAVENITIS_REQUEST_DELAY_S)

        logger.info(
            "sklavenitis: total offers yielded={} across up to {} pages",
            total,
            SKLAVENITIS_MAX_PAGES,
        )


# --- helpers --------------------------------------------------------------


def _page_url(page_number: int) -> str:
    if page_number <= 1:
        return SKLAVENITIS_BASE_URL + SKLAVENITIS_OFFERS_PATH
    return f"{SKLAVENITIS_BASE_URL}{SKLAVENITIS_OFFERS_PATH}?pg={page_number}"


def _base_headers(*, referer: str | None) -> dict[str, str]:
    """The set of headers a real Chrome on macOS sends for navigation.

    curl_cffi already injects the right ``sec-ch-ua`` / ``user-agent``
    for the chosen impersonation profile; we only add language &
    referer hints here so we don't fight its defaults.
    """
    headers = {
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;q=0.9,"
            "image/avif,image/webp,image/apng,*/*;q=0.8"
        ),
        "Accept-Language": "el-GR,el;q=0.9,en-US;q=0.8,en;q=0.7",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin" if referer else "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
    }
    if referer:
        headers["Referer"] = referer
    return headers
