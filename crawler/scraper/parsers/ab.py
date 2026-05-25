"""AB Vassilopoulos GraphQL `ProductList` response → OfferItem parser.

AB's storefront is a Next.js app that fetches its product catalogue
client-side from a GraphQL endpoint at ``https://www.ab.gr/api/v1/``.
The promotion listing comes from the ``ProductList`` operation
(``productListingType="PROMOTION_SEARCH"``) which returns paginated
JSON with ~10 products per page and rich, structured promotion data.

We bypass Playwright entirely and call that endpoint over plain
HTTP. The spider deals with pagination; this parser turns a single
response body into a stream of OfferItems.

Filtering policy
----------------
AB tags a *lot* of products with "X Plus points for Y articles" —
the AB loyalty-points promo. Those products are at their regular
price; the "offer" is loyalty currency, not a price drop. For the
MVP offer-aggregator scope we only emit products with an actual
discounted price, signalled by ``price.showStrikethroughPrice ==
True`` plus a numeric ``discountedPriceFormatted``. Loyalty-only
items can be opted in later if/when we model that promotion class.
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable

from loguru import logger

from scraper.items import OfferItem

# Absolute URL prefix for product `url` and `images[].url` (both come back
# as site-relative paths from the GraphQL API).
AB_BASE_URL = "https://www.ab.gr"

# AB's promo titles encode the discount percentage in the visible label
# (e.g. "Κέρδος 15%"). The numeric ``percentageDiscount`` field on the
# Promotion type is null for the BuyXGetPercentageOff variant, so we
# regex it out of the title as a fallback.
_DISCOUNT_PCT_RE = re.compile(r"(\d{1,3})\s*%")

# Date format used by every Promotion.{start,end}Date field.
_PROMO_DT_FMT = "%d/%m/%Y %H:%M:%S"


def extract_offers_from_payload(
    payload: dict[str, Any], scraped_at: datetime
) -> Iterable[OfferItem]:
    """Yield OfferItems from a parsed GraphQL ``ProductList`` JSON body."""
    products = ((payload or {}).get("data") or {}).get("productList") or {}
    products = products.get("products") or []
    logger.debug("ab-parser: {} products in payload", len(products))

    for product in products:
        item = _offer_from_product(product, scraped_at)
        if item is not None:
            yield item


def extract_offers(json_text: str, scraped_at: datetime) -> Iterable[OfferItem]:
    """Convenience wrapper that parses raw JSON text first."""
    try:
        payload = json.loads(json_text)
    except json.JSONDecodeError as exc:
        logger.warning("ab-parser: failed to decode payload JSON: {}", exc)
        return iter(())
    return extract_offers_from_payload(payload, scraped_at)


# --- internals ------------------------------------------------------------


def _offer_from_product(
    product: dict[str, Any], scraped_at: datetime
) -> OfferItem | None:
    price_block = product.get("price") or {}

    # Only emit real price-drop offers. Loyalty-points promos leave
    # showStrikethroughPrice = False even when a Promotion object exists.
    if not price_block.get("showStrikethroughPrice"):
        return None

    sale_price = _parse_formatted_price(price_block.get("discountedPriceFormatted"))
    if sale_price is None:
        # Fall back to ``unitPrice`` if the formatted field is missing — but
        # only if we still have a strikethrough flag. If both are missing
        # there's nothing useful to ship.
        sale_price = _to_decimal(price_block.get("unitPrice"))
        if sale_price is None:
            return None

    original_price = _to_decimal(price_block.get("value"))

    # If somehow sale >= original, the "discount" is bogus; treat as no
    # original (we'd rather miss data than misrepresent a price).
    if original_price is not None and original_price <= sale_price:
        original_price = None

    promo = _pick_displayed_promotion(product.get("potentialPromotions") or [])
    discount_pct: int | None = None
    valid_from: date | None = None
    valid_to: date | None = None
    if promo is not None:
        discount_pct = _extract_discount_pct(promo, original_price, sale_price)
        valid_from = _promo_date(promo.get("startDate"))
        valid_to = _promo_date(promo.get("endDate"))

    name = (product.get("name") or "").strip() or None
    if not name:
        return None

    code = product.get("code")
    external_id = str(code) if code is not None else None

    canonical = product.get("url") or ""
    url = AB_BASE_URL + canonical if canonical.startswith("/") else (canonical or None)

    image_url = _pick_image(product.get("images") or [])

    category = ((product.get("firstLevelCategory") or {}).get("name") or None)
    if category:
        category = category.strip() or None

    unit = (price_block.get("supplementaryPriceLabel2") or price_block.get("unit") or None)
    if unit:
        unit = unit.strip() or None

    return OfferItem(
        external_id=external_id,
        name=name,
        url=url,
        image_url=image_url,
        category=category,
        unit=unit,
        price=sale_price,
        original_price=original_price,
        discount_pct=discount_pct,
        currency=price_block.get("currencyIso") or "EUR",
        valid_from=valid_from,
        valid_to=valid_to,
        scraped_at=scraped_at,
    )


def _pick_displayed_promotion(promotions: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Pick the promotion that drives the visible discount.

    AB sometimes stacks a loyalty-points promo on top of a real price drop
    (e.g. "Κέρδος 15% + 50 AB Plus πόντοι"). The price-drop one is what
    matters for our offer record. Heuristic: prefer promotions whose
    title looks like "...N%" (a percentage badge); fall back to
    ``toDisplay`` flag; fall back to the first entry.
    """
    if not promotions:
        return None

    percentage = [p for p in promotions if _DISCOUNT_PCT_RE.search(p.get("title") or "")]
    if percentage:
        return percentage[0]

    displayable = [p for p in promotions if p.get("toDisplay")]
    if displayable:
        return displayable[0]

    return promotions[0]


def _extract_discount_pct(
    promo: dict[str, Any], original: Decimal | None, sale: Decimal
) -> int | None:
    """Pull the discount percent from the promo or compute it as fallback."""
    # 1. Trust the numeric field if AB populated it.
    raw = promo.get("percentageDiscount")
    if isinstance(raw, (int, float)) and 0 <= int(raw) <= 100:
        return int(raw)

    # 2. Regex out of the title — that's where "Κέρδος 15%" lives.
    title = promo.get("title") or ""
    match = _DISCOUNT_PCT_RE.search(title)
    if match:
        pct = int(match.group(1))
        if 0 <= pct <= 100:
            return pct

    # 3. Compute from original vs sale when we have both. Round to nearest
    # integer; if the rounding sits outside [0,100] something is off and
    # we'd rather return None than misreport.
    if original is not None and original > 0:
        try:
            computed = int(round((original - sale) / original * 100))
        except (InvalidOperation, ZeroDivisionError):
            return None
        if 0 <= computed <= 100:
            return computed

    return None


def _pick_image(images: list[dict[str, Any]]) -> str | None:
    """Pick the best image URL — prefer the larger 'xlarge', fall back to first."""
    if not images:
        return None

    by_format: dict[str, str] = {}
    for img in images:
        fmt = (img or {}).get("format") or ""
        url = (img or {}).get("url") or ""
        if fmt and url and fmt not in by_format:
            by_format[fmt] = url

    for preferred in ("xlarge", "zoom", "respListGrid", "small"):
        url = by_format.get(preferred)
        if url:
            return AB_BASE_URL + url if url.startswith("/") else url

    # Last resort: first image of any format.
    first = (images[0] or {}).get("url")
    if first:
        return AB_BASE_URL + first if first.startswith("/") else first
    return None


def _parse_formatted_price(formatted: str | None) -> Decimal | None:
    """Parse AB's price strings like "€6,08" / "€10,10" into Decimal."""
    if not formatted:
        return None
    # Strip currency symbol and any whitespace; comma is the decimal sep.
    cleaned = formatted.replace("€", "").strip().replace(".", "").replace(",", ".")
    try:
        return Decimal(cleaned)
    except (InvalidOperation, ValueError):
        return None


def _promo_date(raw: str | None) -> date | None:
    """Parse ``"13/05/2026 21:00:00"`` (CET) into a date."""
    if not raw:
        return None
    try:
        return datetime.strptime(raw, _PROMO_DT_FMT).date()
    except ValueError:
        return None


def _to_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
