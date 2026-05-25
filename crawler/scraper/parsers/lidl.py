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

Price-block shapes observed in the wild
---------------------------------------
A single card can expose its price under one of two siblings of
``regionsPrices.<region>``:

* ``currentPrice``: a single object — used once the promotion has
  *started*. This is what live, in-flight offers look like.
* ``futurePrices``: a list of objects each wrapping ``price`` — used
  for upcoming promotions that haven't started yet.

Both inner ``price`` blocks share the same field layout (``price``,
``oldPrice``, ``discount.percentageDiscount``, ``packaging.text``,
``startDate`` / ``endDate``, ``currencyCode`` …), so we normalise on
the first available block. Historically only ``futurePrices`` was
checked — that quietly dropped the entire current-week catalogue once
the Thursday rollover flipped offers from "future" to "current"
(observed 2026-05-25: every kw22 evdomadiaies card moved to
``currentPrice`` and the spider's priced-offer count collapsed from
~85 to ~27). See ``crawler/tests/test_lidl_parser.py`` for both
shapes pinned against committed fixtures.
"""

from __future__ import annotations

import html as htmllib
import json
import re
from collections.abc import Iterable
from datetime import date, datetime
from typing import Any

from loguru import logger

from scraper.items import OfferItem
from scraper.normalize import to_decimal

# Every product card on a listing page wraps itself in an element carrying
# ``data-grid-data="<HTML-entity-encoded JSON>"``. One attribute per product.
_GRID_DATA_RE = re.compile(r'data-grid-data="([^"]+)"')

LIDL_BASE_URL = "https://www.lidl-hellas.gr"


def extract_offers(html_text: str, scraped_at: datetime) -> Iterable[OfferItem]:
    """Yield OfferItem instances for every *discounted* product on a Lidl listing page.

    Cards without a current sale price (``regionsPrices`` missing or empty)
    are skipped — we only emit offers, not bare products. In addition,
    cards that have a price block but carry **no real promo signal**
    (no ``percentageDiscount > 0``, no ``deletedPrice > price``,
    no ``discountText`` like "-20%") are also skipped — the campaign
    pages include "everyday low price" cards alongside the weekly
    flyer items, and the public ``/offers`` endpoint must only show
    items that actually carry a discount. See module docstring.
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
    # cross-prefecture campaigns later. We pick the first region that
    # carries any usable price block (``currentPrice`` for live promos
    # OR ``futurePrices`` for upcoming ones); downstream we can revisit
    # if real multi-region data appears.
    price_block: dict[str, Any] | None = None
    for candidate in regions_prices.values():
        block = _pick_price_block(candidate or {})
        if block is not None:
            price_block = block
            break
    if price_block is None:
        return None
    sale_price = to_decimal(price_block.get("price"))
    if sale_price is None:
        return None

    # ``/offers`` is a "weekly promotions" surface, not a full catalogue.
    # Lidl campaign pages mix two card types in the same grid: cards on
    # promotion this week (carry a `discount` block with a percentage,
    # an `oldPrice`, or a `discountText`) and cards at their everyday
    # shelf price (no `discount` block, no `oldPrice`). Emitting both
    # would leak the catalogue into a feed that promises offers. Gate
    # on a real promo signal and skip the rest silently.
    if not _has_promo_signal(price_block):
        return None

    discount_block: dict[str, Any] = price_block.get("discount") or {}
    original_price = to_decimal(
        price_block.get("oldPrice") or discount_block.get("deletedPrice")
    )
    # If the only signal was a `discountText` that didn't carry through
    # to a numeric original price, refuse to misreport: leave it None.
    if original_price is not None and sale_price is not None and original_price <= sale_price:
        original_price = None
    discount_pct_raw = discount_block.get("percentageDiscount")
    discount_pct = _to_int_in_range(discount_pct_raw, lo=0, hi=100)

    # Lidl's data-grid-data exposes single-unit % discounts only — no
    # BOGOF / multi-buy metadata. When a discount exists we synthesise
    # a short label ("−15%") and tag the row as `strikethrough` so the
    # frontend renders the new promo pill on the same code path AB uses;
    # otherwise both fields stay null and the legacy "no badge" rendering
    # applies.
    promo_label: str | None = None
    promo_type: str | None = None
    if discount_pct is not None and discount_pct > 0:
        promo_label = f"−{discount_pct}%"
        promo_type = "strikethrough"
    elif original_price is None:
        # Promo signal was the ``discountText`` only (no numeric pct,
        # no oldPrice). Surface that text verbatim so the row carries
        # a real promo_label downstream — the backend's defensive
        # validator requires at least one of discount_pct /
        # promo_label / original_price>price.
        raw_text = (discount_block.get("discountText") or "").strip()
        if raw_text:
            promo_label = raw_text[:80]
            promo_type = "strikethrough"

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
        promo_label=promo_label,
        promo_type=promo_type,
        currency=price_block.get("currencyCode") or "EUR",
        valid_from=valid_from,
        valid_to=valid_to,
        scraped_at=scraped_at,
    )


def _has_promo_signal(price_block: dict[str, Any]) -> bool:
    """Return True iff ``price_block`` carries any evidence of a real discount.

    A "real" Lidl promo manifests in one of three observable ways:

    1. ``discount.percentageDiscount`` > 0 — explicit "-15%" / "-20%" etc.
    2. ``discount.discountText`` non-empty and starts with a minus sign
       — Lidl uses both ASCII '-' and Unicode '−' (U+2212) for "−20%"
       / "-€2"-style copy.
    3. ``oldPrice`` (or ``discount.deletedPrice``) set AND strictly
       greater than ``price`` — the canonical strikethrough shape.

    Cards that satisfy none of these are everyday-shelf-price tiles
    sharing the same grid markup. We skip them so the ``/offers``
    surface contains only items that actually went on offer.
    """
    sale = to_decimal(price_block.get("price"))
    if sale is None:
        return False
    discount_block = price_block.get("discount") or {}
    pct = discount_block.get("percentageDiscount")
    if isinstance(pct, (int, float)) and pct > 0:
        return True
    text = discount_block.get("discountText")
    if isinstance(text, str):
        stripped = text.strip()
        # Accept "-20%" / "−20%" / "-€2" / "−€2" copy.
        if stripped.startswith(("-", "−")) and any(ch.isdigit() for ch in stripped):
            return True
    old = to_decimal(price_block.get("oldPrice") or discount_block.get("deletedPrice"))
    if old is not None and old > sale:
        return True
    return False


def _pick_price_block(region: dict[str, Any]) -> dict[str, Any] | None:
    """Return the active price dict for a region, or None if absent.

    Lidl exposes the same inner shape under two different keys depending
    on whether the promotion is already running or scheduled:

    * ``regionsPrices.<region>.currentPrice`` — single dict, live offer.
    * ``regionsPrices.<region>.futurePrices`` — list of ``{"price": {...}}``
      wrappers, used for upcoming offers.

    We prefer ``currentPrice`` when both are present (a live offer always
    wins over a future one for the same product), falling back to the first
    ``futurePrices`` entry. Returns ``None`` when neither is populated —
    that's an "online-only" / banner / RETAIL-without-promotion card and
    must be skipped silently.
    """
    current = region.get("currentPrice")
    if isinstance(current, dict) and current.get("price") is not None:
        return current

    future_prices = region.get("futurePrices") or []
    if future_prices:
        first = future_prices[0] or {}
        wrapped = first.get("price")
        if isinstance(wrapped, dict) and wrapped.get("price") is not None:
            return wrapped

    return None


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
