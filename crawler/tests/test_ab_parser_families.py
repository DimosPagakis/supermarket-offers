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
from datetime import datetime, UTC
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
SCRAPED_AT = datetime(2026, 5, 25, 12, 0, 0, tzinfo=UTC)


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
    in the same price/original/pct values the legacy test asserts and
    the new promo_label / promo_type enrichment that ships alongside."""
    items = _load(FIXTURE_FAMILIES)
    eggs = next(off for fam, off in items if off and off.external_id == "7606160")
    assert eggs.price == Decimal("6.08")
    assert eggs.original_price == Decimal("7.15")
    assert eggs.discount_pct == 15
    # SHT is the one family where the legacy maths is honest, so the row
    # carries BOTH the numeric pct AND the brand's badge title. The FE
    # will prefer the label when both are present.
    assert eggs.promo_type == "strikethrough"
    assert eggs.promo_label is not None
    assert "%" in eggs.promo_label


# --- BXG% (Buy X Get Percentage Off, no strikethrough) -------------------


def test_buy_x_get_percent_off_emits_shelf_price_with_label() -> None:
    """Product 7132459 is a 400g pack of peas on a "-30% στα 2" deal.

    Pre-2026-05-25 we quoted the per-unit effective price (1.50€) which
    misled shoppers — at the till one unit rings up at 2.14€, the -30%
    only triggers once the basket holds two. We now emit the regular
    shelf price as ``price``, leave ``original_price`` / ``discount_pct``
    null, and carry the savings narrative in ``promo_label``.
    """
    items = _load(FIXTURE_FAMILIES)
    found = [(fam, off) for fam, off in items if off and off.external_id == "7132459"]
    assert len(found) == 1
    fam, peas = found[0]
    assert fam == FAMILY_BXG_PCT
    # The shelf price wins. Multi-buy effective per-unit is a lie at the
    # single-unit till.
    assert peas.price == Decimal("2.14")
    assert peas.original_price is None
    assert peas.discount_pct is None
    # The brand's own copy is what shoppers see on the AB page.
    assert peas.promo_type == "bxg_percent"
    assert peas.promo_label is not None
    assert "30" in peas.promo_label and "%" in peas.promo_label
    # Multi-buy promos still carry their start/end dates.
    assert peas.valid_from is not None
    assert peas.valid_to is not None


# --- BXGY (Buy X Get Y free) ---------------------------------------------


def test_one_plus_one_free_emits_shelf_price_with_bxgy_label() -> None:
    """Product 7125700 is a "1 + 1 free" cereal bar at 3.80€.

    Repro case for the bug: AB's site shows the shopper "€3.80" with a
    "1+1 δώρο" sticker. The old behaviour quoted the effective per-unit
    "€1.90" with a -50% pill on our card and the shopper felt misled
    when they clicked through. We now emit the shelf price + the
    verbatim badge label.
    """
    items = _load(FIXTURE_FAMILIES)
    bars = next(off for fam, off in items if off and off.external_id == "7125700")
    assert bars.price == Decimal("3.80")
    assert bars.original_price is None
    assert bars.discount_pct is None
    assert bars.promo_type == "bxgy_free"
    assert bars.promo_label is not None
    # AB ships English BOGOF titles ("1 + 1 free") in the GraphQL
    # response; the storefront renders the Greek "1+1 δώρο" sticker.
    # We localise to match the shopper-facing text.
    assert bars.promo_label == "1+1 δώρο"


def test_three_plus_one_free_emits_shelf_price_with_bxgy_label() -> None:
    """Product 7085201 has ``qualifyingCount=4`` and ``freeCount=None`` —
    the "3 + 1 free" structure is only in the title. The parser still
    parses (paid, free) as a malformed-promo gate, but no longer uses
    them to compute an effective per-unit price."""
    items = _load(FIXTURE_FAMILIES)
    cat_food = next(off for fam, off in items if off and off.external_id == "7085201")
    assert cat_food.price == Decimal("0.95")
    assert cat_food.original_price is None
    assert cat_food.discount_pct is None
    assert cat_food.promo_type == "bxgy_free"
    assert cat_food.promo_label is not None
    assert "3" in cat_food.promo_label and "+" in cat_food.promo_label


# --- DISCOUNT_EUROS ------------------------------------------------------


def test_discount_euros_for_y_articles_emits_shelf_price_with_label() -> None:
    """Product 7084612: olive sauce 3.18€ on "-0.8€ στα 2".

    Same fix-direction as BXG% / BXGY: shelf price wins, label
    carries the deal. Per-unit effective maths would lie when the
    shopper buys one.
    """
    items = _load(FIXTURE_FAMILIES)
    sauce = next(off for fam, off in items if off and off.external_id == "7084612")
    assert sauce.price == Decimal("3.18")
    assert sauce.original_price is None
    assert sauce.discount_pct is None
    assert sauce.promo_type == "discount_euros"
    assert sauce.promo_label is not None
    # Title is "-0.8€ στα 2" or similar — must mention the euro sign.
    assert "€" in sauce.promo_label


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
