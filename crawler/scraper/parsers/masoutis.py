"""Masoutis promo-API response → OfferItem parser.

Masoutis's storefront fetches promotional products from a JSON endpoint:
``POST /api/eshop/GetPromoItemWithListCouponsSubCategoriesAutoPromosv2``.
Body is ``{"PassKey": "Sc@NnSh0p", ...}`` and the response is a flat
list of product objects (~50 active promo items at the time of
capture).

The endpoint is signed: every request carries three custom headers
(``uid``, ``usl``, ``key``) that the storefront's JS computes from a
secret. Replaying the request from outside the browser context gets
a 403. The spider works around that by driving Playwright once to
fetch the response with the browser's auth context, then handing
the JSON to this parser.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from datetime import datetime
from typing import Any

from loguru import logger

from scraper.items import OfferItem
from scraper.normalize import to_decimal

MASOUTIS_BASE_URL = "https://www.masoutis.gr"

# Discount strings come back as "-45%", "-30%". Captures the integer.
_DISCOUNT_RE = re.compile(r"-?(\d{1,3})\s*%")


def extract_offers_from_payload(
    payload: Any, scraped_at: datetime
) -> Iterable[OfferItem]:
    """Yield OfferItems from a parsed promo-API response (a JSON list)."""
    if not isinstance(payload, list):
        logger.warning(
            "masoutis-parser: expected list payload, got {}", type(payload).__name__
        )
        return
    logger.debug("masoutis-parser: {} items in payload", len(payload))
    for product in payload:
        item = _offer_from_product(product, scraped_at)
        if item is not None:
            yield item


def extract_offers(json_text: str, scraped_at: datetime) -> Iterable[OfferItem]:
    """Convenience wrapper that parses raw JSON text first."""
    try:
        payload = json.loads(json_text)
    except json.JSONDecodeError as exc:
        logger.warning("masoutis-parser: failed to decode payload JSON: {}", exc)
        return iter(())
    return extract_offers_from_payload(payload, scraped_at)


# --- internals ------------------------------------------------------------


def _offer_from_product(
    product: dict[str, Any], scraped_at: datetime
) -> OfferItem | None:
    # PosPrice is the current sale price; StartPrice is the regular price.
    sale_price = to_decimal(product.get("PosPrice"))
    if sale_price is None or sale_price <= 0:
        return None

    original_price = to_decimal(product.get("StartPrice"))
    # Defensive: if Masoutis ever ships a record with StartPrice == PosPrice
    # or 0, treat as no original price rather than misreport.
    if original_price is not None and original_price <= sale_price:
        original_price = None

    discount_pct = _parse_discount_pct(product.get("Discount"))

    name = (product.get("ItemDescr") or "").strip() or None
    if not name:
        return None

    code = product.get("Itemcode")
    external_id = str(code) if code not in (None, "") else None

    canonical = product.get("ItemDescrLink") or ""
    if canonical.startswith("http"):
        url = canonical
    elif canonical.startswith("/"):
        url = MASOUTIS_BASE_URL + canonical
    else:
        url = None

    image_url = product.get("PhotoData") or None
    if image_url and image_url.startswith("/"):
        image_url = MASOUTIS_BASE_URL + image_url

    # ``BrandNameDesciption`` (sic — Masoutis ships that typo) is the
    # closest thing to a category at the brand level. Their real
    # category lives in ``OfferCategoryDescr`` but it's null in the
    # observed payload; prefer it when present so we don't lose info if
    # they start populating it.
    category = (
        product.get("OfferCategoryDescr") or product.get("BrandNameDesciption") or None
    )
    if category:
        category = str(category).strip() or None

    # ``ItemVolume`` is the cheapest signal of unit ("15.99€/κιλ"). Fall
    # back to ``StartPrItemVolume`` ("29.07€") which sometimes carries
    # the packaging weight prefix when ItemVolume is empty.
    unit = (
        product.get("ItemVolume")
        or product.get("StartPrItemVolume")
        or None
    )
    if unit:
        unit = str(unit).strip() or None

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
        currency="EUR",
        valid_from=None,
        valid_to=None,
        scraped_at=scraped_at,
    )


def _parse_discount_pct(raw: Any) -> int | None:
    if raw is None:
        return None
    match = _DISCOUNT_RE.search(str(raw))
    if not match:
        return None
    pct = int(match.group(1))
    if 0 <= pct <= 100:
        return pct
    return None


