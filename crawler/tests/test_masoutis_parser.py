"""Integration test for the Masoutis promo-API response parser.

Run against a committed snapshot of the promo-item-list endpoint
captured 2026-05-25 from
``POST /api/eshop/GetPromoItemWithListCouponsSubCategoriesAutoPromosv2``.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from scraper.items import OfferItem
from scraper.parsers.masoutis import extract_offers

FIXTURE = (
    Path(__file__).parent / "fixtures" / "masoutis" / "promoitem-page0.json"
)
SCRAPED_AT = datetime(2026, 5, 25, 12, 0, 0, tzinfo=timezone.utc)


def _load_offers() -> list[OfferItem]:
    return list(extract_offers(FIXTURE.read_text(encoding="utf-8"), SCRAPED_AT))


def test_extracts_all_priced_offers() -> None:
    """The fixture lists 50 promotional products with PosPrice + StartPrice
    populated. Parser should emit one OfferItem per row."""
    offers = _load_offers()
    assert len(offers) == 50, f"expected 50 offers, got {len(offers)}"


def test_first_offer_field_mapping() -> None:
    """End-to-end map of the first product (Nirvana ice cream)."""
    offer = _load_offers()[0]

    # Greek title is preserved (no transliteration, no whitespace damage).
    assert offer.name == "Nirvana Παγωτό Cookie Dough 302γρ./420ml."

    # Itemcode (string in the payload) becomes external_id.
    assert offer.external_id == "4003935"

    # PosPrice (4.83) is the sale price; StartPrice (8.78) is the original.
    assert offer.price == Decimal("4.83")
    assert offer.original_price == Decimal("8.78")

    # Discount "-45%" → discount_pct=45.
    assert offer.discount_pct == 45

    # Currency is hardcoded EUR — Masoutis doesn't expose it per-row.
    assert offer.currency == "EUR"

    # Image is an absolute URL on Masoutis's blob storage.
    assert offer.image_url is not None
    assert offer.image_url.startswith("https://masoutisimagesneu.blob.core.windows.net/")

    # ItemDescrLink already absolute.
    assert offer.url == (
        "https://www.masoutis.gr/categories/item/"
        "nirvana-pagwto-cookie-dough-302gr-420ml-?4003935"
    )

    # No validity dates exposed by the API.
    assert offer.valid_from is None
    assert offer.valid_to is None


def test_payload_round_trip_matches_backend_contract() -> None:
    offer = _load_offers()[0]
    payload = offer.to_payload()
    for key in (
        "external_id",
        "name",
        "url",
        "image_url",
        "category",
        "unit",
        "price",
        "original_price",
        "discount_pct",
        "currency",
        "valid_from",
        "valid_to",
        "scraped_at",
    ):
        assert key in payload, f"missing key in offer payload: {key}"

    assert payload["price"] == 4.83
    assert payload["original_price"] == 8.78
    assert payload["discount_pct"] == 45
    # Dates are null in the API; payload should reflect that.
    assert payload["valid_from"] is None
    assert payload["valid_to"] is None
