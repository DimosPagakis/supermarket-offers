"""My Market HTML listing → OfferItem parser.

My Market renders ``/offers`` as a server-side-rendered HTML grid:
35 product cards per page, paginated via ``?page=N``. Every card is
a ``<div class="product--teaser ..." data-id="<id>">`` element
carrying:
  * the product name in ``h3 > a > p`` (and again in
    ``data-google-analytics-item-param`` JSON for SKU and category),
  * the displayed price split across two spans —
    ``.teaser-display-price-whole`` (integer euros) and
    ``.teaser-display-price-fraction`` (cents),
  * an image with ``data-main-image="<id>"``,
  * an absolute product URL via the heading anchor.

The ``data-google-analytics-item-param`` JSON also carries a ``price``
field, but it's the per-display-unit price (€/g for "Τιμή Κιλού"
products) and would mislead a shopper. We read the displayed price
out of the DOM spans instead — that's what the customer sees.

Discounted-only emit policy (2026-05-25)
----------------------------------------
``/offers`` is misnamed — it ships the chain's full active catalogue
plus a handful of items decorated with promotional UI. Of 35 cards
on a typical page, only ~20% carry a real discount signal. To stop
the catalogue leaking onto the public ``/offers`` API, the parser
gates emission on one of:

* a ``span.diagonal-line`` element — strikethrough original price
  (typically the per-kg / per-unit prior figure inside the price
  analysis block); present on every real "ΠΡΟΣΦΟΡΑ" / "-N%" card,
* a ``.offer-note--percent`` element — the explicit "-N%" pill.

Cards with neither signal are catalogue tiles ("SUPER ΤΙΜΗ" is a
low-everyday-price sticker, **not** a real promo) and are skipped
silently. When a card carries a strikethrough we additionally parse
the original price and synthesise a ``discount_pct`` / ``promo_label``
/ ``promo_type='strikethrough'`` so the frontend pill renders.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from collections.abc import Iterable

from loguru import logger
from parsel import Selector

from scraper.items import OfferItem

MYMARKET_BASE_URL = "https://www.mymarket.gr"

# Match "-25%" / "−25%" inside the offer-note--percent pill. Accept both
# ASCII minus and the unicode "−" (U+2212).
_PERCENT_RE = re.compile(r"[-−]?\s*(\d{1,3})\s*%")


def extract_total_pages(html_text: str) -> int | None:
    """Return the highest ``?page=N`` link advertised in the listing's
    pagination nav, or ``None`` if no pagination is present.

    My Market's pagination block renders direct anchors for the first few
    pages, an ellipsis, then the final couple of pages. We pick the
    maximum integer out of every ``data-mkey="page-<N>"`` anchor — that
    matches the "go to last page" link the user sees in the UI.

    Returns ``None`` (not ``1``) when no page anchors are present so the
    caller can distinguish "listing has zero pagination block" (treat as
    a single page) from "listing parser broke" (warn).
    """
    sel = Selector(text=html_text)
    keys = sel.css('nav a::attr(data-mkey)').getall()
    page_numbers: list[int] = []
    for key in keys:
        if not key or not key.startswith("page-"):
            continue
        try:
            page_numbers.append(int(key[len("page-"):]))
        except ValueError:
            continue
    if not page_numbers:
        return None
    return max(page_numbers)


def extract_offers(html_text: str, scraped_at: datetime) -> Iterable[OfferItem]:
    """Yield OfferItems for every product card on a My Market listing page."""
    sel = Selector(text=html_text)
    cards = sel.xpath('//*[contains(@class,"product--teaser")]')
    logger.debug("mymarket-parser: {} product--teaser cards on page", len(cards))

    seen_ids: set[str] = set()
    for card in cards:
        offer = _offer_from_card(card, scraped_at)
        if offer is None:
            continue
        key = offer.external_id or offer.name
        if key in seen_ids:
            continue
        seen_ids.add(key)
        yield offer


# --- internals ------------------------------------------------------------


def _offer_from_card(card: Selector, scraped_at: datetime) -> OfferItem | None:
    # Reconstruct the displayed price from the two-span layout. Fall back
    # to None if either piece is missing — partial prices would be worse
    # than no offer.
    whole = (card.css(".teaser-display-price-whole::text").get() or "").strip()
    fraction = (card.css(".teaser-display-price-fraction::text").get() or "").strip()
    if not whole or not fraction:
        return None
    price = _compose_price(whole, fraction)
    if price is None:
        return None

    # Discounted-only emit gate (see module docstring). Keep the card
    # only if it carries a real promo signal — a strikethrough
    # ``diagonal-line`` original price somewhere in the card, or the
    # explicit ``-N%`` pill in ``offer-note--percent``. Cards carrying
    # only the "SUPER ΤΙΜΗ" sticker are everyday-low-price catalogue
    # tiles, not real promos, and must be skipped.
    has_diagonal = bool(card.xpath('.//*[contains(@class, "diagonal-line")]').get())
    percent_text = card.css(".offer-note--percent::text").get()
    discount_pct = _parse_discount_pct(percent_text)
    if not has_diagonal and discount_pct is None:
        return None

    # Optional: synthesise the FE pill when we have a numeric %. We
    # deliberately do not populate ``original_price`` from the
    # diagonal-line value — that figure is the per-kg / per-unit
    # comparator price, not the headline strikethrough on ``price``.
    promo_label: str | None = None
    promo_type: str | None = None
    if discount_pct is not None and discount_pct > 0:
        promo_label = f"−{discount_pct}%"
        promo_type = "strikethrough"
    elif has_diagonal:
        # Strikethrough present but no explicit % pill. Surface the
        # brand's own copy ("ΠΡΟΣΦΟΡΑ") when present, else fall back
        # to a generic label so the FE pill renders and the row
        # carries a non-null ``promo_label`` (the backend's defensive
        # promo-signal validator requires at least one of
        # original_price/discount_pct/promo_label).
        msg = (card.css(".offer-note--message::text").get() or "").strip()
        promo_label = msg if msg and "ΠΡΟΣΦΟΡΑ" in msg else "ΠΡΟΣΦΟΡΑ"
        promo_type = "strikethrough"

    # Pull the analytics JSON blob — best source for SKU + category, since
    # those aren't reliably exposed in surface DOM.
    analytics_raw = card.css("h3 a::attr(data-google-analytics-item-param)").get()
    analytics: dict[str, Any] = {}
    if analytics_raw:
        try:
            analytics = json.loads(analytics_raw)
        except json.JSONDecodeError as exc:
            logger.warning(
                "mymarket-parser: failed to decode analytics blob: {}", exc
            )

    name = (
        card.css("h3 a p::text").get()
        or card.css("h3 a::attr(aria-label)").get()
        or analytics.get("name")
        or ""
    )
    name = (name or "").strip()
    if name.endswith(" teaser"):
        # ``aria-label`` is "<name> teaser"; strip the suffix.
        name = name[: -len(" teaser")].strip()
    if not name:
        return None

    sku = analytics.get("id") or card.attrib.get("data-id")
    external_id = str(sku) if sku else None

    href = card.css("h3 a::attr(href)").get()
    if href and href.startswith("/"):
        url = MYMARKET_BASE_URL + href
    elif href and href.startswith("http"):
        url = href
    else:
        url = None

    # The product image. Prefer the one tagged with this card's data-id.
    image_url = card.css("img[data-main-image]::attr(src)").get()

    # Category breadcrumb. The analytics blob carries the deepest level.
    category = (
        analytics.get("category3")
        or analytics.get("category2")
        or analytics.get("category")
        or None
    )
    if category:
        category = category.strip() or None

    return OfferItem(
        external_id=external_id,
        name=name,
        url=url,
        image_url=image_url,
        category=category,
        unit=None,
        price=price,
        original_price=None,
        discount_pct=discount_pct,
        promo_label=promo_label,
        promo_type=promo_type,
        currency="EUR",
        valid_from=None,
        valid_to=None,
        scraped_at=scraped_at,
    )


def _parse_discount_pct(raw: str | None) -> int | None:
    """Pull the integer percent out of an ``offer-note--percent`` pill text.

    Pills observed in the wild: "-25%", "−30%". Returns None when the
    pill is absent or the text doesn't carry a plausible 0..100 integer.
    """
    if not raw:
        return None
    match = _PERCENT_RE.search(raw)
    if not match:
        return None
    try:
        pct = int(match.group(1))
    except ValueError:
        return None
    if 0 <= pct <= 100:
        return pct
    return None


def _compose_price(whole: str, fraction: str) -> Decimal | None:
    """Glue "0" + "72" → Decimal("0.72")."""
    # Strip any stray "€" / whitespace just in case.
    whole = whole.replace("€", "").strip()
    fraction = fraction.replace("€", "").strip()
    if not whole.isdigit() or not fraction.isdigit():
        return None
    # Pad / truncate fraction to two digits — My Market always uses two,
    # but being defensive keeps us out of the weeds if a future variant
    # ships single-digit cents.
    fraction = fraction[:2].rjust(2, "0")
    try:
        return Decimal(f"{whole}.{fraction}")
    except InvalidOperation:
        return None
