"""AB Vassilopoulos GraphQL `ProductList` response → OfferItem parser.

AB's storefront is a Next.js app that fetches its product catalogue
client-side from a GraphQL endpoint at ``https://www.ab.gr/api/v1/``.
The promotion listing comes from the ``ProductList`` operation
(``productListingType="PROMOTION_SEARCH"``) which returns paginated
JSON with ~10 products per page and rich, structured promotion data.

We bypass Playwright entirely and call that endpoint over plain
HTTP. The spider deals with pagination; this parser turns a single
response body into a stream of OfferItems.

Filtering / emission policy (2026-05-25)
----------------------------------------
AB's ``/search/promotions`` page mixes six promotion families. We
classify each product and decide per family whether it represents
something we can faithfully quote as a "price-comparable offer":

* ``SHT_TRUE`` — ``price.showStrikethroughPrice == True``. Single-unit
  price drop. Original = ``price.value``, sale = ``discountedPriceFormatted``.
  **Emitted.** This is the 282-offer baseline.

* ``BXG%_no_SHT`` — ``promotionType="Buy X Get Percentage Off All Products"``
  *without* a strikethrough, e.g. "−30% στα 2". You only get the
  discount when you buy ``qualifyingCount`` units; per-unit effective
  price = ``value × (1 − pct/100)``. **Emitted** with the conditional
  unit price as ``price``, original = ``value``. Caller-side prose may
  want to mention "from 2 units" — the unit-count is encoded in the
  promo title, which we keep accessible via ``unit`` when relevant.

* ``BXGY_FREE`` — ``promotionType="Grocery Buy X get Y free"``, e.g.
  "1 + 1 δώρο" (qualifyingCount=2, freeCount=1). Effective per-unit
  price = ``value × (qualifyingCount − freeCount) / qualifyingCount``.
  **Emitted.** discount_pct = freeCount / qualifyingCount × 100.

* ``DISCOUNT_EUROS`` — ``promotionType="Discount X Euros For Y Articles"``,
  e.g. "−0.8€ στα 2". Effective per-unit price = ``value − (euros /
  qualifyingCount)``. **Emitted.** discount_pct computed from the
  resulting ratio.

* ``FIXED_POINTS_THRESHOLD`` — "Spend N€ get M points". Pure loyalty
  with a basket condition; doesn't change the displayed unit price.
  **Skipped.**

* ``PLUS_POINTS`` — ``promotionType="X Plus points for Y articles"``.
  Pure loyalty per article; same regular price as everywhere else.
  **Skipped.** This is the noise that was inflating AB's "promotions"
  page; comparing it across chains is apples-to-oranges (other chains
  don't ship loyalty-only entries in their offers feed).

The first four families together accounted for 405 of 853 products
in the 2026-05-25 capture; the broader policy roughly doubles AB's
ingest versus the strikethrough-only baseline.
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

# Match "−0.8€" / "-0,8€" / "0.8€" anywhere in a promo title or message.
# We accept both ASCII '-' and the unicode minus '−' (U+2212), with
# either '.' or ',' as decimal separator.
_DISCOUNT_EUROS_RE = re.compile(r"[-−]?\s*(\d+(?:[.,]\d+)?)\s*€")

# Match BOGOF titles like "1 + 1 free", "2 + 1 free", "3 + 1 δώρο".
# Captures paid-count then free-count. AB localises the "free" word
# ("free" / "δώρο"), so we just match the structural "N + M ...".
_BXGY_TITLE_RE = re.compile(r"(\d+)\s*\+\s*(\d+)")

# Date format used by every Promotion.{start,end}Date field.
_PROMO_DT_FMT = "%d/%m/%Y %H:%M:%S"

# --- promotion families -------------------------------------------------

#: Families we accept and translate into an OfferItem with an effective price.
FAMILY_SHT = "SHT_TRUE"
FAMILY_BXG_PCT = "BXG%_no_SHT"
FAMILY_BXGY_FREE = "BXGY_FREE"
FAMILY_DISCOUNT_EUROS = "DISCOUNT_EUROS"

#: Families we recognise but deliberately skip — they don't change the
#: displayed per-unit price, so cross-chain comparison would mislead.
FAMILY_FIXED_POINTS = "FIXED_POINTS_THRESHOLD"
FAMILY_PLUS_POINTS = "PLUS_POINTS"

#: Anything we don't have a mapping for. Logged at DEBUG and skipped so
#: a new AB promo type doesn't silently corrupt prices.
FAMILY_UNKNOWN = "UNKNOWN"

#: Convenience set used by the spider for its closed() audit log.
EMITTED_FAMILIES = frozenset(
    {FAMILY_SHT, FAMILY_BXG_PCT, FAMILY_BXGY_FREE, FAMILY_DISCOUNT_EUROS}
)


def extract_offers_from_payload(
    payload: dict[str, Any], scraped_at: datetime
) -> Iterable[OfferItem]:
    """Yield OfferItems from a parsed GraphQL ``ProductList`` JSON body.

    Use ``extract_offers_with_family`` if you need the per-product
    classification (the spider does, to surface a histogram in
    ``closed()``).
    """
    for family, offer in extract_offers_with_family(payload, scraped_at):
        if offer is not None:
            yield offer


def extract_offers_with_family(
    payload: dict[str, Any], scraped_at: datetime
) -> Iterable[tuple[str, OfferItem | None]]:
    """Yield ``(family, offer)`` pairs for *every* product in the payload.

    ``offer`` is ``None`` when the product belongs to a non-emitted family
    (loyalty-only, unknown). The spider uses this to keep a histogram of
    families seen across the run.
    """
    products = ((payload or {}).get("data") or {}).get("productList") or {}
    products = products.get("products") or []
    logger.debug("ab-parser: {} products in payload", len(products))

    for product in products:
        family, offer = _classify_and_build(product, scraped_at)
        yield family, offer


def extract_offers(json_text: str, scraped_at: datetime) -> Iterable[OfferItem]:
    """Convenience wrapper that parses raw JSON text first."""
    try:
        payload = json.loads(json_text)
    except json.JSONDecodeError as exc:
        logger.warning("ab-parser: failed to decode payload JSON: {}", exc)
        return iter(())
    return extract_offers_from_payload(payload, scraped_at)


# --- internals ------------------------------------------------------------


def _classify_and_build(
    product: dict[str, Any], scraped_at: datetime
) -> tuple[str, OfferItem | None]:
    """Pick the promotion family for ``product`` and (where applicable)
    build the OfferItem.

    Returns ``(family, offer_or_none)``. We always return *some* family
    so the spider can count what AB shipped, even when we deliberately
    skip the item.
    """
    price_block = product.get("price") or {}
    promotions = product.get("potentialPromotions") or []

    # SHT_TRUE wins regardless of which promotionType labels are attached.
    # AB sometimes stacks loyalty on top of a strikethrough.
    if price_block.get("showStrikethroughPrice"):
        return FAMILY_SHT, _build_sht_offer(product, scraped_at)

    # No strikethrough: classify by the strongest promotion attached.
    promo, family = _pick_offer_promotion(promotions)
    if family == FAMILY_BXG_PCT:
        return family, _build_bxg_percent_offer(product, promo, scraped_at)
    if family == FAMILY_BXGY_FREE:
        return family, _build_bxgy_free_offer(product, promo, scraped_at)
    if family == FAMILY_DISCOUNT_EUROS:
        return family, _build_discount_euros_offer(product, promo, scraped_at)

    # Loyalty-only or unknown — count but don't emit.
    return family, None


def _pick_offer_promotion(
    promotions: list[dict[str, Any]],
) -> tuple[dict[str, Any] | None, str]:
    """From the per-product promotion list, pick the one we'd emit on.

    Priority order matches the storefront's visible badge precedence:

    1. ``Buy X Get Percentage Off`` (real % discount, possibly multi-buy)
    2. ``Grocery Buy X get Y free`` (BOGOF / 2+1 etc.)
    3. ``Discount X Euros For Y Articles`` (multi-buy euro discount)
    4. ``Fixed Points For Threshold Promotion`` → loyalty, skipped
    5. ``X Plus points for Y articles`` → loyalty, skipped
    6. anything else → unknown, skipped

    Returns ``(promo_or_None, family)``.
    """
    if not promotions:
        return None, FAMILY_UNKNOWN

    by_type: dict[str, dict[str, Any]] = {}
    for p in promotions:
        t = (p or {}).get("promotionType") or ""
        # Multiple promos of the same type → take the first toDisplay one,
        # else the first.
        if t not in by_type:
            by_type[t] = p
        elif p.get("toDisplay") and not by_type[t].get("toDisplay"):
            by_type[t] = p

    if "Buy X Get Percentage Off All Products" in by_type:
        return by_type["Buy X Get Percentage Off All Products"], FAMILY_BXG_PCT
    if "Grocery Buy X get Y free" in by_type:
        return by_type["Grocery Buy X get Y free"], FAMILY_BXGY_FREE
    if "Discount X Euros For Y Articles" in by_type:
        return by_type["Discount X Euros For Y Articles"], FAMILY_DISCOUNT_EUROS
    if "Fixed Points For Threshold Promotion" in by_type:
        return by_type["Fixed Points For Threshold Promotion"], FAMILY_FIXED_POINTS
    if "X Plus points for Y articles" in by_type:
        return by_type["X Plus points for Y articles"], FAMILY_PLUS_POINTS

    # Everything else — including "Grocery Multi-buy" variants we haven't
    # specifically modelled. Log once at DEBUG so we notice new families.
    unknown_types = sorted(by_type.keys())
    logger.debug("ab-parser: skipping unknown promotion families: {}", unknown_types)
    return None, FAMILY_UNKNOWN


# --- OfferItem builders, one per emitted family --------------------------


def _build_sht_offer(
    product: dict[str, Any], scraped_at: datetime
) -> OfferItem | None:
    """Real single-unit price drop (legacy / pre-2026-05-25 behaviour)."""
    price_block = product.get("price") or {}

    sale_price = _parse_formatted_price(price_block.get("discountedPriceFormatted"))
    if sale_price is None:
        # Fall back to ``unitPrice`` if the formatted field is missing.
        sale_price = _to_decimal(price_block.get("unitPrice"))
        if sale_price is None:
            return None

    original_price = _to_decimal(price_block.get("value"))
    # If somehow sale >= original, the "discount" is bogus; drop the
    # original-price claim rather than misrepresent it.
    if original_price is not None and original_price <= sale_price:
        original_price = None

    promo = _pick_displayed_strikethrough_promo(product.get("potentialPromotions") or [])
    discount_pct: int | None = None
    valid_from: date | None = None
    valid_to: date | None = None
    if promo is not None:
        discount_pct = _extract_discount_pct(promo, original_price, sale_price)
        valid_from = _promo_date(promo.get("startDate"))
        valid_to = _promo_date(promo.get("endDate"))

    return _finalise_offer(
        product=product,
        sale_price=sale_price,
        original_price=original_price,
        discount_pct=discount_pct,
        valid_from=valid_from,
        valid_to=valid_to,
        scraped_at=scraped_at,
    )


def _build_bxg_percent_offer(
    product: dict[str, Any],
    promo: dict[str, Any] | None,
    scraped_at: datetime,
) -> OfferItem | None:
    """Multi-buy / single-buy % off without strikethrough, e.g. "−30% στα 2".

    Effective per-unit price = original × (1 − pct/100). We always quote
    the conditional unit price because that's the lowest price the
    shopper can actually pay for this product right now; multi-buy
    qualifying counts are noted in the promo title.
    """
    price_block = product.get("price") or {}
    original_price = _to_decimal(price_block.get("value"))
    if original_price is None or promo is None:
        return None

    pct = _extract_discount_pct(promo, original_price, original_price)
    if pct is None or pct <= 0:
        return None

    factor = (Decimal(100) - Decimal(pct)) / Decimal(100)
    sale_price = (original_price * factor).quantize(Decimal("0.01"))
    if sale_price <= 0 or sale_price >= original_price:
        return None

    return _finalise_offer(
        product=product,
        sale_price=sale_price,
        original_price=original_price,
        discount_pct=int(pct),
        valid_from=_promo_date(promo.get("startDate")),
        valid_to=_promo_date(promo.get("endDate")),
        scraped_at=scraped_at,
    )


def _build_bxgy_free_offer(
    product: dict[str, Any],
    promo: dict[str, Any] | None,
    scraped_at: datetime,
) -> OfferItem | None:
    """BOGOF / 2+1: per-unit effective price = value × (paid)/(paid+free).

    AB encodes the deal as ``qualifyingCount = paid+free`` and
    ``freeCount = free``. So "1+1 free" → qualifyingCount=2, freeCount=1.
    Effective ratio = (qualifyingCount − freeCount) / qualifyingCount.
    """
    if promo is None:
        return None
    price_block = product.get("price") or {}
    original_price = _to_decimal(price_block.get("value"))
    if original_price is None or original_price <= 0:
        return None

    paid, free = _parse_bxgy_counts(promo)
    if paid is None or free is None:
        return None
    qualifying = paid + free
    sale_price = (original_price * Decimal(paid) / Decimal(qualifying)).quantize(Decimal("0.01"))
    if sale_price <= 0 or sale_price >= original_price:
        return None

    discount_pct = int(round(Decimal(free) / Decimal(qualifying) * Decimal(100)))
    return _finalise_offer(
        product=product,
        sale_price=sale_price,
        original_price=original_price,
        discount_pct=discount_pct,
        valid_from=_promo_date(promo.get("startDate")),
        valid_to=_promo_date(promo.get("endDate")),
        scraped_at=scraped_at,
    )


def _build_discount_euros_offer(
    product: dict[str, Any],
    promo: dict[str, Any] | None,
    scraped_at: datetime,
) -> OfferItem | None:
    """Multi-buy euro discount, e.g. "-0.8€ στα 2".

    Per-unit effective price = original − (euros / qualifyingCount).
    The euro amount is encoded in the title / simplePromotionMessage,
    not as a structured field.
    """
    if promo is None:
        return None
    price_block = product.get("price") or {}
    original_price = _to_decimal(price_block.get("value"))
    if original_price is None or original_price <= 0:
        return None

    qualifying = promo.get("qualifyingCount") or 1
    if not isinstance(qualifying, int) or qualifying <= 0:
        return None

    euros_off = _extract_euro_discount(promo)
    if euros_off is None or euros_off <= 0:
        return None

    per_unit_off = euros_off / Decimal(qualifying)
    sale_price = (original_price - per_unit_off).quantize(Decimal("0.01"))
    if sale_price <= 0 or sale_price >= original_price:
        return None

    discount_pct = int(round((original_price - sale_price) / original_price * Decimal(100)))
    if not 0 < discount_pct <= 100:
        discount_pct = None  # type: ignore[assignment]

    return _finalise_offer(
        product=product,
        sale_price=sale_price,
        original_price=original_price,
        discount_pct=discount_pct,
        valid_from=_promo_date(promo.get("startDate")),
        valid_to=_promo_date(promo.get("endDate")),
        scraped_at=scraped_at,
    )


def _finalise_offer(
    *,
    product: dict[str, Any],
    sale_price: Decimal,
    original_price: Decimal | None,
    discount_pct: int | None,
    valid_from: date | None,
    valid_to: date | None,
    scraped_at: datetime,
) -> OfferItem | None:
    """Common tail of the per-family builders: map static product fields."""
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

    price_block = product.get("price") or {}
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


def _pick_displayed_strikethrough_promo(
    promotions: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """For strikethrough products, pick the promotion that drives the
    visible discount.

    AB sometimes stacks a loyalty-points promo on top of a real price drop
    (e.g. "Κέρδος 15% + 50 AB Plus πόντοι"). The price-drop one is what
    matters. Heuristic: prefer promotions whose title contains "...N%";
    fall back to ``toDisplay`` flag; fall back to the first entry.
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

    # 2. Regex out of the title — "Κέρδος 15%" / "-30% στα 2".
    title = promo.get("title") or ""
    match = _DISCOUNT_PCT_RE.search(title)
    if match:
        pct = int(match.group(1))
        if 0 <= pct <= 100:
            return pct

    # 3. Compute from original vs sale when we have both. Round to nearest
    # integer; if the rounding sits outside [0,100] something is off and
    # we'd rather return None than misreport.
    if original is not None and original > 0 and sale != original:
        try:
            computed = int(round((original - sale) / original * 100))
        except (InvalidOperation, ZeroDivisionError):
            return None
        if 0 <= computed <= 100:
            return computed

    return None


def _parse_bxgy_counts(
    promo: dict[str, Any],
) -> tuple[int | None, int | None]:
    """Return ``(paid, free)`` for a "Buy X Get Y free" promotion.

    The numeric ``qualifyingCount`` field reliably gives the total units
    in the deal (paid + free), but ``freeCount`` is frequently null on
    AB's response — the convention "N + M" is only encoded in the
    title ("1 + 1 free", "2 + 1 δώρο"). When freeCount is missing we
    parse "N + M" from the title and derive ``paid = N``, ``free = M``.
    """
    title = promo.get("title") or ""
    match = _BXGY_TITLE_RE.search(title)
    if match:
        paid = int(match.group(1))
        free = int(match.group(2))
        if paid > 0 and free > 0:
            return paid, free

    # Fallback to structured counts if AB populated them.
    qualifying = promo.get("qualifyingCount")
    free = promo.get("freeCount")
    if isinstance(qualifying, int) and isinstance(free, int) and qualifying > free > 0:
        return qualifying - free, free
    return None, None


def _extract_euro_discount(promo: dict[str, Any]) -> Decimal | None:
    """Parse the euro amount from a "Discount X Euros For Y Articles" promo.

    AB encodes the figure in the title ("-0.8€ στα 2") and in
    simplePromotionMessage ("Με 2 προϊόν(τα) κερδίζεις 0.8€"). Both
    parse the same way; try title first because it's the shorter string.
    """
    for key in ("title", "simplePromotionMessage", "description"):
        raw = promo.get(key) or ""
        match = _DISCOUNT_EUROS_RE.search(raw)
        if not match:
            continue
        figure = match.group(1).replace(",", ".")
        try:
            value = Decimal(figure)
        except (InvalidOperation, ValueError):
            continue
        if value > 0:
            return value
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
