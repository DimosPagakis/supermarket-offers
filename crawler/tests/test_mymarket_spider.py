"""Spider-level behaviour test for MyMarketSpider.

Exercises the empty-page-tolerance logic added 2026-05-28 — the
original implementation stopped at the first zero-yield page and
capped real coverage at ~26 offers out of ~150-page catalogue.
The replacement tolerates ``MYMARKET_EMPTY_PAGE_RUN`` consecutive
empty pages before giving up.

We bypass the Scrapy engine entirely and call ``parse`` directly
with a hand-crafted ``Response``, asserting the spider yields a
``next_page`` Request (i.e. doesn't bail) until the empty streak
crosses the threshold.
"""

from __future__ import annotations

from pathlib import Path

import scrapy
from scrapy.http import HtmlResponse, Request

from scraper.spiders.mymarket import (
    MYMARKET_EMPTY_PAGE_RUN,
    MYMARKET_OFFERS_URL,
    MyMarketSpider,
)

EMPTY_PAGE_HTML = (
    "<html><body><div class='pagination'>"
    "<a data-mkey='page-1'>1</a>"
    "<a data-mkey='page-5'>5</a>"
    "</div></body></html>"
)


def _empty_response(page: int) -> HtmlResponse:
    url = MYMARKET_OFFERS_URL if page == 1 else f"{MYMARKET_OFFERS_URL}?page={page}"
    return HtmlResponse(
        url=url,
        body=EMPTY_PAGE_HTML.encode("utf-8"),
        encoding="utf-8",
        request=Request(url=url, meta={"page_number": page}),
    )


def _next_request(parsed) -> Request | None:
    for item in parsed:
        if isinstance(item, Request):
            return item
    return None


def test_zero_yield_page_does_not_stop_pagination() -> None:
    spider = MyMarketSpider()
    response = _empty_response(3)
    # total_pages pre-seeded so we exercise the empty-streak path, not
    # the "ran past total_pages" termination.
    response.request.meta.update(total_pages=200, empty_streak=0)
    nxt = _next_request(spider.parse(response))
    # The page had 0 offers, but the streak counter is still under the
    # threshold so we expect a next-page Request.
    assert nxt is not None, "spider bailed on the first empty page"
    assert nxt.meta["page_number"] == 4
    assert nxt.meta["empty_streak"] == 1


def test_streak_bails_after_threshold() -> None:
    spider = MyMarketSpider()
    response = _empty_response(MYMARKET_EMPTY_PAGE_RUN)
    response.request.meta.update(
        page_number=MYMARKET_EMPTY_PAGE_RUN,
        total_pages=200,
        empty_streak=MYMARKET_EMPTY_PAGE_RUN - 1,
    )
    nxt = _next_request(spider.parse(response))
    # One more empty page lifts the streak to MYMARKET_EMPTY_PAGE_RUN
    # which trips the bail-out — no follow-up Request.
    assert nxt is None, "spider kept walking past the empty-streak threshold"


def test_real_page_resets_streak(tmp_path: Path) -> None:
    """A page that yields offers must reset the streak so a later
    dry-spell still gets the full ``MYMARKET_EMPTY_PAGE_RUN`` budget."""
    fixture = Path(__file__).parent / "fixtures" / "mymarket" / "listing-page1.html"
    spider = MyMarketSpider()
    response = HtmlResponse(
        url=f"{MYMARKET_OFFERS_URL}?page=3",
        body=fixture.read_bytes(),
        encoding="utf-8",
        request=Request(
            url=f"{MYMARKET_OFFERS_URL}?page=3",
            meta={
                "page_number": 3,
                "total_pages": 161,
                "empty_streak": MYMARKET_EMPTY_PAGE_RUN - 1,
            },
        ),
    )
    nxt = _next_request(spider.parse(response))
    assert nxt is not None
    assert nxt.meta["empty_streak"] == 0, "real-offer page didn't reset the empty streak"
