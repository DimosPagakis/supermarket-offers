"""Lidl Hellas listing-page parser.

Lidl renders weekly offer pages at URLs like
``/c/evdomadiaies-epiloges-26kw22/a10095458`` (or themed variants such
as ``/c/poiotita-poikilia-26kw22/...``). Every product card on the
listing embeds its full domain model in a ``data-grid-data`` HTML
attribute as HTML-entity-encoded JSON. That JSON is the source of
truth — it contains structured prices, validity windows, discount
percentages, images, canonical URLs, and packaging strings.

We parse that JSON instead of chasing CSS selectors over the rendered
DOM because:
  * It's vastly more stable across UI rebrands.
  * It already separates current price / old price / discount, which
    saves us from heuristically diffing strike-through text.
  * It carries machine-readable ``startDate`` / ``endDate`` which map
    cleanly to the backend's ``valid_from`` / ``valid_to`` columns.

The downside is schema drift: if Lidl renames ``oldPrice`` or moves
prices out of ``regionsPrices.<region>.futurePrices[0].price``, we
break. That risk is mitigated by the integration test in
``crawler/tests/test_lidl_parser.py`` which exercises this module
against a real, committed fixture.
"""

from __future__ import annotations

import html as htmllib
import json
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable

from loguru import logger

from scraper.items import OfferItem

# Every product card on a listing page wraps itself in an element carrying
# ``data-grid-data="<HTML-entity-encoded JSON>"``. One attribute per product.
_GRID_DATA_RE = re.compile(r'data-grid-data="([^"]+)"')

LIDL_BASE_URL = "https://www.lidl-hellas.gr"


def extract_offers(html_text: str, scraped_at: datetime) -> Iterable[OfferItem]:
    """Yield OfferItem instances for every priced product on a Lidl listing page.

    Cards without a current sale price (``regionsPrices`` missing or empty)
    are skipped — we only emit offers, not bare products.
    """
    raw_attrs = _GRID_DATA_RE.findall(html_text)
    logger.debug("lidl-parser: found {} data-grid-data attributes", len(raw_attrs))

    seen_ids: set[str] = set()
    for raw in raw_attrs:
        try:
            data = json.loads(htmllib.unescape(raw))
        except json.JSONDecodeError as exc:
            logger.warning("lidl-parser: failed to decode data-grid-data JSON: {}", exc)
            continue

        item = _offer_from_grid_data(data, scraped_at)
        if item is None:
            continue

        # Deduplicate within a single page — Lidl occasionally renders the
        # same product in multiple grid sections (e.g. "highlight" + "all").
        # The backend would happily store both as separate Offer rows since
        # they're for the same Product + crawl_run, but it's noise.
        key = item.external_id or item.name
        if key in seen_ids:
            continue
        seen_ids.add(key)

        yield item


# --- internals ------------------------------------------------------------


def _offer_from_grid_data(data: dict[str, Any], scraped_at: datetime) -> OfferItem | None:
    """Map a single decoded grid-data dict to an OfferItem.

    Returns None when the card carries no current price (e.g. "online-only"
    cards or featured banners that share the same wrapper element). We
    deliberately bail early rather than emit a half-built item.
    """
    regions_prices = data.get("regionsPrices") or {}
    if not regions_prices:
        return None

    # Region key is consistently "1" in observed fixtures, but iterate to
    # stay schema-tolerant — Lidl may expose multi-region pricing for
    # cross-prefecture campaigns later. We pick the first region with
    # populated futurePrices; downstream we can revisit if real
    # multi-region data appears.
    region_block: dict[str, Any] | None = None
    for candidate in regions_prices.values():
        if (candidate or {}).get("futurePrices"):
            region_block = candidate
            break
    if region_block is None:
        return None

    future_prices = region_block.get("futurePrices") or []
    if not future_prices:
        return None

    # First futurePrice is the "current/next" promotion block. Lidl
    # occasionally lists more than one when a multi-week campaign overlaps;
    # we'd revisit if that ever surfaces real data we need.
    price_block: dict[str, Any] = future_prices[0].get("price") or {}
    sale_price = _to_decimal(price_block.get("price"))
    if sale_price is None:
        return None

    discount_block: dict[str, Any] = price_block.get("discount") or {}
    original_price = _to_decimal(
        price_block.get("oldPrice") or discount_block.get("deletedPrice")
    )
    discount_pct_raw = discount_block.get("percentageDiscount")
    discount_pct = _to_int_in_range(discount_pct_raw, lo=0, hi=100)

    title = (data.get("title") or "").strip() or None
    if not title:
        # No human-readable name means we can't dedupe / match downstream.
        return None

    product_id = data.get("productId")
    external_id = str(product_id) if product_id is not None else None

    canonical = data.get("canonicalUrl") or ""
    url: str | None
    if canonical.startswith("http"):
        url = canonical
    elif canonical.startswith("/"):
        url = LIDL_BASE_URL + canonical
    else:
        url = None

    image_url = _first_image(data)

    # ``packaging.text`` is short and shopper-facing ("208 φύλλα (720 g)",
    # "Το κιλό"). Closest semantic match to our ``unit`` column without
    # introducing a separate "packaging" field.
    packaging_text = (price_block.get("packaging") or {}).get("text")

    valid_from = _iso_to_date(price_block.get("startDate"))
    valid_to = _iso_to_date(price_block.get("endDate"))

    return OfferItem(
        external_id=external_id,
        name=title,
        url=url,
        image_url=image_url,
        category=data.get("category"),
        unit=packaging_text,
        price=sale_price,
        original_price=original_price,
        discount_pct=discount_pct,
        currency=price_block.get("currencyCode") or "EUR",
        valid_from=valid_from,
        valid_to=valid_to,
        scraped_at=scraped_at,
    )


def _first_image(data: dict[str, Any]) -> str | None:
    """Pick the first image URL out of the various Lidl image arrays."""
    for key in ("imageList_V1", "imageList"):
        items = data.get(key) or []
        if items:
            first = items[0] or {}
            url = first.get("image") if isinstance(first, dict) else None
            if url:
                return url
    # Some cards expose a flat ``image`` field instead of a list.
    flat = data.get("image") or data.get("image_V1")
    if isinstance(flat, str):
        return flat
    return None


def _to_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _to_int_in_range(value: Any, *, lo: int, hi: int) -> int | None:
    if value is None:
        return None
    try:
        n = int(value)
    except (TypeError, ValueError):
        return None
    if lo <= n <= hi:
        return n
    return None


def _iso_to_date(value: str | None) -> date | None:
    """Parse Lidl's ISO timestamps ("2026-05-27T21:00Z") into a date.

    We deliberately collapse the timestamp to a date — the backend stores
    ``valid_from`` / ``valid_to`` as dates and the time-of-day in Lidl's
    payload is the campaign rollover moment in CET, not something a shopper
    cares about.
    """
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt.date()
