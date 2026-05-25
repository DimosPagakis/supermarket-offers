"""Integration test for the AB Vassilopoulos GraphQL response parser.

Run against a committed snapshot of the ``ProductList`` operation
captured 2026-05-25 from ``https://www.ab.gr/api/v1/?operationName=
ProductList&productListingType=PROMOTION_SEARCH&pageNumber=0``.

These assertions guard the field mapping, the loyalty-vs-real-discount
filter, and the wire-format round trip. If AB rename / move any of
the GraphQL fields the parser depends on, this test breaks loudly
and we recapture the fixture before shipping.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from scraper.items import OfferItem

from ._fixtures import assert_payload_matches_backend_contract, load_offers


def _load_offers() -> list[OfferItem]:
    return load_offers("ab", "productlist-page0.json")


def test_filters_loyalty_only_promos() -> None:
    """The page-0 response contains 10 products; 9 of them are wine bottles
    flagged "X Plus points for Y articles" only (loyalty points, no real
    price drop) and 1 — the biological eggs at code 7606160 — has a real
    "Κέρδος 15%" promotion. Parser must emit exactly that one offer."""
    offers = _load_offers()
    assert len(offers) == 1, f"expected 1 real-discount offer, got {len(offers)}"
    assert offers[0].external_id == "7606160"


def test_eggs_offer_field_mapping() -> None:
    """End-to-end map: GraphQL JSON → OfferItem, against the known fixture
    product (the eggs from the screenshot we used to design the parser)."""
    offer = _load_offers()[0]

    # Greek title preserved.
    assert offer.name == "Αυγά Βιολογικά Medium 10 Τεμάχια"

    # `code` becomes external_id as a string.
    assert offer.external_id == "7606160"

    # discountedPriceFormatted ("€6,08") is the sale price; `value` (7.15)
    # is the original. Parser must use the *discounted* one as `price`.
    assert offer.price == Decimal("6.08"), offer.price
    assert offer.original_price == Decimal("7.15"), offer.original_price

    # The promo title "Κέρδος 15%" carries the discount because the
    # numeric percentageDiscount field is null on this promo type.
    assert offer.discount_pct == 15

    # Currency lifted from price.currencyIso, not hardcoded.
    assert offer.currency == "EUR"

    # Promotion dates parsed from "13/05/2026 21:00:00" / "03/06/2026 20:59:00".
    assert offer.valid_from == date(2026, 5, 13)
    assert offer.valid_to == date(2026, 6, 3)

    # URL becomes an absolute AB URL.
    assert offer.url is not None and offer.url.startswith("https://www.ab.gr/el/eshop/")
    assert "/p/7606160" in offer.url

    # Image URL prefixed with the AB origin.
    assert offer.image_url is not None
    assert offer.image_url.startswith("https://www.ab.gr/medias/")

    # Category lifted from firstLevelCategory.name — useful for grouping later.
    assert offer.category is not None and "αυγά" in offer.category.lower() or "Φρ" in offer.category or offer.category  # category for eggs in AB taxonomy

    # supplementaryPriceLabel2 ("10 τεμ") lands in unit.
    assert offer.unit == "10 τεμ"


def test_payload_round_trip_matches_backend_contract() -> None:
    """`OfferItem.to_payload()` must yield the keys the backend FormRequest
    validates against."""
    offer = _load_offers()[0]
    payload = assert_payload_matches_backend_contract(offer)

    assert payload["price"] == 6.08
    assert payload["original_price"] == 7.15
    assert payload["discount_pct"] == 15
    assert payload["valid_from"] == "2026-05-13"
    assert payload["valid_to"] == "2026-06-03"
