"""Integration test for the Masoutis promo-API response parser.

Run against a committed snapshot of the promo-item-list endpoint
captured 2026-05-25 from
``POST /api/eshop/GetPromoItemWithListCouponsSubCategoriesAutoPromosv2``.
"""

from __future__ import annotations

from decimal import Decimal

from scraper.items import OfferItem
from scraper.parsers.masoutis import extract_offers_from_payload

from ._fixtures import (
    SCRAPED_AT,
    assert_payload_matches_backend_contract,
    load_offers,
)


def _load_offers() -> list[OfferItem]:
    return load_offers("masoutis", "promoitem-page0.json")


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

    # Masoutis is single-unit strikethrough — the raw "Discount" string
    # surfaces verbatim as the promo label and the structured kind is
    # `strikethrough`.
    assert offer.promo_type == "strikethrough"
    assert offer.promo_label == "-45%"

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
    payload = assert_payload_matches_backend_contract(offer)

    assert payload["price"] == 4.83
    assert payload["original_price"] == 8.78
    assert payload["discount_pct"] == 45
    assert payload["promo_label"] == "-45%"
    assert payload["promo_type"] == "strikethrough"
    # Dates are null in the API; payload should reflect that.
    assert payload["valid_from"] is None
    assert payload["valid_to"] is None


# ---------------------------------------------------------------------------
# Pagination — the Masoutis spider walks ``IfWeight`` pages until a page
# returns fewer than 50 items. The parser itself is page-agnostic; these
# tests verify that the spider can safely feed it page-by-page payloads
# and that the parser doesn't choke on the short final page.
# ---------------------------------------------------------------------------


def _product_stub(itemcode: int) -> dict:
    """Minimal Masoutis promo row, just enough for the parser to keep it."""
    return {
        "Itemcode": itemcode,
        "ItemDescr": f"Synthetic product {itemcode}",
        "ItemDescrLink": (
            f"https://www.masoutis.gr/categories/item/synthetic-{itemcode}"
        ),
        "PhotoData": "https://example.com/img.jpg",
        "PosPrice": "1.23",
        "StartPrice": "2.00",
        "Discount": "-39%",
        "BrandNameDesciption": "Synthetic",
        "ItemVolume": "1τμχ",
    }


def test_parser_handles_multi_page_concatenation() -> None:
    """Walk two synthetic ``IfWeight`` pages through the parser and
    confirm the offers from both surface independently — i.e. the spider
    can call ``extract_offers_from_payload`` per page and accumulate."""
    page1 = [_product_stub(i) for i in range(50)]
    page2 = [_product_stub(i) for i in range(50, 87)]  # short final page

    offers = []
    for page in (page1, page2):
        offers.extend(extract_offers_from_payload(page, SCRAPED_AT))

    assert len(offers) == 87
    # External IDs must remain distinct — no cross-page collision.
    external_ids = [o.external_id for o in offers]
    assert len(set(external_ids)) == 87


def test_parser_handles_empty_final_page() -> None:
    """A defensively-empty page (zero items) should yield zero offers
    without raising — that's the spider's terminal stop condition."""
    offers = list(extract_offers_from_payload([], SCRAPED_AT))
    assert offers == []


def test_parser_short_page_signals_end_of_catalogue() -> None:
    """A page < 50 items is the storefront's "this is the last page"
    signal; the parser still emits every row, the spider stops after."""
    short_page = [_product_stub(i) for i in range(37)]
    offers = list(extract_offers_from_payload(short_page, SCRAPED_AT))
    assert len(offers) == 37
