"""Per-promotion-family integration tests for the AB parser.

These exercise the broader 2026-05-25 emit policy (see
``scraper/parsers/ab.py`` docstring) using fixtures captured live from
``https://www.ab.gr/api/v1/?operationName=ProductList&productListing
Type=PROMOTION_SEARCH`` on 2026-05-25.

There are two fixtures:

* ``productlist-promo-families.json`` — 11 hand-picked products, one
  for each promotion family. Cheap to read, easy to scan when an
  assertion fails. Use it for spot checks of the per-family field
  mapping.
* ``productlist-all-pages.json`` — the full 853-product capture from
  the same crawl. Used to lock in the global emit count so a future
  policy change makes the impact obvious in the diff.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from scraper.items import OfferItem
from scraper.parsers.ab import (
    EMITTED_FAMILIES,
    FAMILY_BXG_PCT,
    FAMILY_BXGY_FREE,
    FAMILY_DISCOUNT_EUROS,
    FAMILY_FIXED_POINTS,
    FAMILY_PLUS_POINTS,
    FAMILY_SHT,
    extract_offers_with_family,
)

FIXTURE_FAMILIES = Path(__file__).parent / "fixtures" / "ab" / "productlist-promo-families.json"
FIXTURE_ALL = Path(__file__).parent / "fixtures" / "ab" / "productlist-all-pages.json"
SCRAPED_AT = datetime(2026, 5, 25, 12, 0, 0, tzinfo=timezone.utc)


def _load(path: Path) -> list[tuple[str, OfferItem | None]]:
    import json
    payload = json.loads(path.read_text(encoding="utf-8"))
    return list(extract_offers_with_family(payload, SCRAPED_AT))


def _by_code(items: list[tuple[str, OfferItem | None]]) -> dict[str, tuple[str, OfferItem | None]]:
    return {
        (off.external_id if off else f"miss:{i}"): (fam, off)
        for i, (fam, off) in enumerate(items)
    }


# --- SHT (legacy) regression ---------------------------------------------


def test_strikethrough_offer_still_emits_with_eggs_values() -> None:
    """The 282-product strikethrough baseline must keep working. The eggs
    product from the original fixture survives in the curated set; lock
    in the same price/original/pct values the legacy test asserts."""
    items = _load(FIXTURE_FAMILIES)
    eggs = next(off for fam, off in items if off and off.external_id == "7606160")
    assert eggs.price == Decimal("6.08")
    assert eggs.original_price == Decimal("7.15")
    assert eggs.discount_pct == 15


# --- BXG% (Buy X Get Percentage Off, no strikethrough) -------------------


def test_buy_x_get_percent_off_emits_conditional_unit_price() -> None:
    """Product 7132459 is a 400g pack of peas on a "-30% στα 2" deal.
    Original 2.14€, expected effective per-unit = 2.14 × 0.70 = 1.498
    which rounds to 1.50."""
    items = _load(FIXTURE_FAMILIES)
    found = [(fam, off) for fam, off in items if off and off.external_id == "7132459"]
    assert len(found) == 1
    fam, peas = found[0]
    assert fam == FAMILY_BXG_PCT
    assert peas.original_price == Decimal("2.14")
    assert peas.price == Decimal("1.50")
    assert peas.discount_pct == 30
    # Multi-buy promos still carry their start/end dates.
    assert peas.valid_from is not None
    assert peas.valid_to is not None


# --- BXGY (Buy X Get Y free) ---------------------------------------------


def test_one_plus_one_free_halves_the_price() -> None:
    """Product 7125700 is a "1 + 1 free" cereal bar at 3.80€.
    Effective per-unit = 1.90€, discount_pct = 50."""
    items = _load(FIXTURE_FAMILIES)
    bars = next(off for fam, off in items if off and off.external_id == "7125700")
    assert bars.original_price == Decimal("3.80")
    assert bars.price == Decimal("1.90")
    assert bars.discount_pct == 50


def test_three_plus_one_free_parses_paid_free_from_title() -> None:
    """Product 7085201 has ``qualifyingCount=4`` and ``freeCount=None`` —
    the "3 + 1 free" structure is only in the title. Parser must fall
    back to title regex. Effective per-unit = 0.95 × 3/4 = 0.7125 → 0.71."""
    items = _load(FIXTURE_FAMILIES)
    cat_food = next(off for fam, off in items if off and off.external_id == "7085201")
    assert cat_food.original_price == Decimal("0.95")
    assert cat_food.price == Decimal("0.71")
    assert cat_food.discount_pct == 25  # 1/4 free


# --- DISCOUNT_EUROS ------------------------------------------------------


def test_discount_euros_for_y_articles_pulls_amount_from_title() -> None:
    """Product 7084612: olive sauce 3.18€ on "-0.8€ στα 2".
    Per-unit off = 0.4€, effective price = 2.78€."""
    items = _load(FIXTURE_FAMILIES)
    sauce = next(off for fam, off in items if off and off.external_id == "7084612")
    assert sauce.original_price == Decimal("3.18")
    assert sauce.price == Decimal("2.78")
    # discount_pct = (3.18 - 2.78) / 3.18 = 12.58% → rounded to 13.
    assert sauce.discount_pct == 13


# --- loyalty families: counted but not emitted ---------------------------


def test_loyalty_points_promos_are_skipped() -> None:
    """``X Plus points for Y articles`` and ``Fixed Points For Threshold
    Promotion`` are pure-loyalty and don't change the displayed price.
    Parser must yield ``offer = None`` for them."""
    items = _load(FIXTURE_FAMILIES)
    families_with_no_offer = {fam for fam, off in items if off is None}
    assert FAMILY_PLUS_POINTS in families_with_no_offer
    assert FAMILY_FIXED_POINTS in families_with_no_offer
    # And conversely: every family in EMITTED_FAMILIES that appears in
    # the fixture must yield at least one OfferItem.
    families_with_offer = {fam for fam, off in items if off is not None}
    assert FAMILY_SHT in families_with_offer
    assert FAMILY_BXG_PCT in families_with_offer
    assert FAMILY_BXGY_FREE in families_with_offer
    assert FAMILY_DISCOUNT_EUROS in families_with_offer
    # Sanity: the constants we expose actually agree with what we emit.
    assert families_with_offer.issubset(EMITTED_FAMILIES)


# --- whole-catalogue regression ------------------------------------------


def test_full_catalogue_emits_405_offers_with_known_family_mix() -> None:
    """Lock in the global count from the 2026-05-25 capture. If a future
    policy change shifts these numbers it's load-bearing — update the
    spider docstring and rebaseline this test together."""
    items = _load(FIXTURE_ALL)
    counts = Counter(fam for fam, _ in items)
    emitted = sum(1 for _, off in items if off is not None)

    assert counts[FAMILY_SHT] == 282
    assert counts[FAMILY_BXG_PCT] == 44
    assert counts[FAMILY_BXGY_FREE] == 69
    assert counts[FAMILY_DISCOUNT_EUROS] == 10
    assert counts[FAMILY_FIXED_POINTS] == 99
    assert counts[FAMILY_PLUS_POINTS] == 349
    assert emitted == 282 + 44 + 69 + 10  # = 405


def test_full_catalogue_every_emitted_item_has_a_sale_price_below_original() -> None:
    """Across all 405 emitted offers, ``price`` should never exceed
    ``original_price`` (which is the whole point of an "offer")."""
    items = _load(FIXTURE_ALL)
    bad = []
    for fam, off in items:
        if off is None:
            continue
        if off.original_price is not None and off.price >= off.original_price:
            bad.append((fam, off.external_id, off.price, off.original_price))
    assert not bad, f"{len(bad)} offers have price >= original_price: {bad[:5]}"
