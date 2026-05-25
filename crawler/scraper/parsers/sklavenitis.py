"""Sklavenitis HTML listing → OfferItem parser.

Sklavenitis renders ``/sylloges/prosfores`` as a server-side HTML grid
of 24 product cards per page, paginated via ``?pg=N``. The page is
fully usable without JS — every card carries enough markup to drive
the listing UI on its own.

Each card is a ``<div class="product …" data-plugin-product="…">``
container that bundles three useful sources of truth:

* ``data-plugin-product`` (JSON): SKU, unit (``unitDisplay``), stock /
  buyability flags.
* ``data-plugin-analyticsimpressions`` (JSON, HTML-entity-encoded):
  ``item_id``, ``item_name``, ``item_brand``, ``item_category`` and a
  numeric ``price`` — the only place on the listing where the price
  is machine-readable, since the visual price lives in mixed-language
  templating ("1,65 €/τεμ.").
* DOM: ``a.absLink`` for the canonical product URL, ``figure img`` for
  the image, ``.priceWrp .price[data-price]`` for the human-readable
  price string ("1,65"), and ``.priceKil`` for the per-kilo / per-litre
  comparison price.

The Akamai bot-manager rejects naive HTTP clients, so the actual
fetching happens in the spider with ``curl_cffi`` (Chrome TLS
impersonation). This module stays I/O-free.

The ``Προσφορές & Χαμηλές Τιμές`` section mixes "real offers" with
"low everyday prices" — Sklavenitis does not visually distinguish the
two on the listing, and there is no per-card "original price" or
"discount %" exposed. The *only* per-card promo signal observable in
the markup is the ``.sign-badges .badge`` "N+M Δώρο" badge that fires
for BOGOF-style flyer items (1 in 24 cards on the typical fixture
page).

Discounted-only emit policy (2026-05-25)
----------------------------------------
``/sylloges/prosfores`` is misnamed — it ships the chain's full
active catalogue. The parser therefore gates emit on the gift-badge
signal: cards without one are catalogue tiles and skipped silently.
This intentionally collapses Sklavenitis's emit count to near zero
on the current listing URL — that's the honest answer until we find
a real flyer entry point. The brand is seeded ``active=false`` to
match (see ``BrandSeeder``); the spider will not run until we point
it at a URL with real promo metadata.
"""

from __future__ import annotations

import html
import json
from collections.abc import Iterable
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from loguru import logger
from parsel import Selector

from scraper.items import OfferItem
from scraper.normalize import to_decimal

SKLAVENITIS_BASE_URL = "https://www.sklavenitis.gr"


def extract_offers(html_text: str, scraped_at: datetime) -> Iterable[OfferItem]:
    """Yield one OfferItem per product card on a Sklavenitis listing page."""
    sel = Selector(text=html_text)
    cards = sel.xpath('//div[@data-plugin-product and contains(@class, "product")]')
    logger.debug("sklavenitis-parser: {} product cards on page", len(cards))

    seen: set[str] = set()
    for card in cards:
        offer = _offer_from_card(card, scraped_at)
        if offer is None:
            continue
        key = offer.external_id or offer.name
        if key in seen:
            continue
        seen.add(key)
        yield offer


# --- internals ------------------------------------------------------------


def _offer_from_card(card: Selector, scraped_at: datetime) -> OfferItem | None:
    # Discounted-only gate: only emit cards carrying a gift-badge promo
    # signal (the lone observable per-card discount marker on the
    # ``/sylloges/prosfores`` listing). Cards without one are catalogue
    # tiles. See module docstring.
    gift_text = _gift_badge_text(card)
    if not gift_text:
        return None

    product_blob = _load_json_attr(card, "data-plugin-product")
    impressions_blob = _load_json_attr(card, "data-plugin-analyticsimpressions")

    item: dict[str, Any] = {}
    if impressions_blob:
        try:
            item = impressions_blob["Call"]["ecommerce"]["items"][0]
        except (KeyError, IndexError, TypeError) as exc:
            logger.warning(
                "sklavenitis-parser: impressions blob missing items[0]: {}", exc
            )

    sku = (
        (item.get("item_id") if item else None)
        or (product_blob.get("sku") if product_blob else None)
    )
    external_id = str(sku).strip() if sku else None

    name = (item.get("item_name") or "").strip() if item else ""
    if not name:
        # Fall back to the visible card title.
        name = (card.css(".product__title a::text").get() or "").strip()
    if not name:
        return None

    category = item.get("item_category") if item else None
    if isinstance(category, str):
        category = category.strip() or None

    # The analytics ``price`` field is a JSON number — authoritative for the
    # displayed shelf price. Fall back to the ``data-price`` attribute if
    # absent (defensive; we haven't seen a card missing it).
    price = _coerce_price(item.get("price") if item else None)
    if price is None:
        price_attr = card.css(".main-price .price::attr(data-price)").get()
        price = _parse_comma_decimal(price_attr)
    if price is None:
        return None

    unit = None
    if product_blob:
        unit_display = product_blob.get("unitDisplay")
        if isinstance(unit_display, str):
            unit = unit_display.strip() or None

    href = card.css("a.absLink::attr(href)").get() or card.css(
        ".product__title a::attr(href)"
    ).get()
    url = _absolute_url(href)

    image_url = card.css("figure img::attr(src)").get()
    if image_url and image_url.startswith("//"):
        image_url = "https:" + image_url

    return OfferItem(
        external_id=external_id,
        name=name,
        url=url,
        image_url=image_url,
        category=category,
        unit=unit,
        price=price,
        original_price=None,
        discount_pct=None,
        promo_label=gift_text,
        promo_type="bxgy_free",
        currency="EUR",
        valid_from=None,
        valid_to=None,
        scraped_at=scraped_at,
    )


def _gift_badge_text(card: Selector) -> str | None:
    """Return the ``N+M Δώρο`` badge text from a card, or ``None`` if absent.

    Sklavenitis surfaces BOGOF-style promos in a ``.sign-badges .badge``
    block that combines ``.gift_number`` ("4+2") and ``.gift_text``
    ("Δώρο"). We stitch those two into a single short label suitable for
    the ``promo_label`` field; absent => caller skips the card.
    """
    number = (card.css(".sign-badges .gift_number::text").get() or "").strip()
    text = (card.css(".sign-badges .gift_text::text").get() or "").strip()
    if not number or not text:
        return None
    composed = f"{number} {text}".strip()
    return composed[:80] if composed else None


def _load_json_attr(card: Selector, attr: str) -> dict[str, Any] | None:
    """Read an HTML attribute carrying JSON (HTML-entity-encoded).

    Sklavenitis stores its plugin payloads in ``data-plugin-*`` attributes
    as JSON with ``&quot;`` for each double quote. parsel's ``::attr()``
    already decodes those entities for us; fall back through ``html.unescape``
    for the odd case where the encoding survived the parser pass.
    """
    raw = card.attrib.get(attr) or card.css(f"::attr({attr})").get()
    if not raw:
        return None
    candidates = [raw]
    if "&quot;" in raw or "&amp;" in raw:
        candidates.append(html.unescape(raw))
    for candidate in candidates:
        try:
            return json.loads(candidate)
        except (json.JSONDecodeError, TypeError):
            continue
    logger.warning("sklavenitis-parser: failed to parse {} JSON blob", attr)
    return None


def _coerce_price(value: Any) -> Decimal | None:
    """Turn a JSON number / numeric string into a Decimal with two places."""
    if isinstance(value, str):
        return _parse_comma_decimal(value)
    return to_decimal(value)


def _parse_comma_decimal(value: str | None) -> Decimal | None:
    """Parse a Greek-formatted decimal like ``"1,65"`` (no thousands sep)."""
    if not value:
        return None
    cleaned = value.strip().replace("€", "").strip()
    if not cleaned:
        return None
    cleaned = cleaned.replace(".", "").replace(",", ".")
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def _absolute_url(href: str | None) -> str | None:
    if not href:
        return None
    href = href.strip()
    if not href:
        return None
    if href.startswith("http://") or href.startswith("https://"):
        return href
    if href.startswith("/"):
        return SKLAVENITIS_BASE_URL + href
    return SKLAVENITIS_BASE_URL + "/" + href
