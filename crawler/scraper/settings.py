"""Scrapy settings for the supermarket-offers crawler.

Kept minimal on purpose — MVP. Tunables come from environment variables so
they can be flipped per-environment without editing code.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

BOT_NAME = "scraper"

SPIDER_MODULES = ["scraper.spiders"]
NEWSPIDER_MODULE = "scraper.spiders"

# Be a polite citizen by default.
ROBOTSTXT_OBEY = True

USER_AGENT = (
    "supermarket-offers-bot/0.1 "
    "(+https://github.com/DimosPagakis/supermarket-offers)"
)

# Throttling. Conservative defaults; AutoThrottle will dial up/down as needed.
DOWNLOAD_DELAY = float(os.getenv("DOWNLOAD_DELAY", "2"))
CONCURRENT_REQUESTS = 8
CONCURRENT_REQUESTS_PER_DOMAIN = 2

AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1.0
AUTOTHROTTLE_MAX_DELAY = 10.0
AUTOTHROTTLE_TARGET_CONCURRENCY = 2.0

# HTTP cache — off by default. Flip HTTPCACHE_ENABLED=1 to speed local iteration.
HTTPCACHE_ENABLED = os.getenv("HTTPCACHE_ENABLED", "0") == "1"
HTTPCACHE_EXPIRATION_SECS = 60 * 60 * 6  # 6 hours
HTTPCACHE_DIR = "httpcache"
HTTPCACHE_IGNORE_HTTP_CODES = [500, 502, 503, 504, 408, 429]
HTTPCACHE_STORAGE = "scrapy.extensions.httpcache.FilesystemCacheStorage"

ITEM_PIPELINES = {
    "scraper.pipelines.BackendPipeline": 300,
}

# Playwright integration — wired up for future spiders (Masoutis, Sklavenitis, ...).
DOWNLOAD_HANDLERS = {
    "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
    "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
}
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
PLAYWRIGHT_BROWSER_TYPE = "chromium"
PLAYWRIGHT_LAUNCH_OPTIONS = {"headless": True}

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Standard Scrapy hygiene
REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
FEED_EXPORT_ENCODING = "utf-8"
