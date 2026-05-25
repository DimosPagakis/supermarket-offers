"""Integration test for the Sklavenitis HTML listing parser.

Run against a committed snapshot of page 1 of
``/sylloges/prosfores/`` captured 2026-05-25 via ``curl_cffi`` (the
Akamai bot-manager rejects naive HTTP clients, see
``crawler/scraper/spiders/sklavenitis.py``).
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from scraper.items import OfferItem
from scraper.parsers.sklavenitis import extract_offers

FIXTURE = (
    Path(__file__).parent / "fixtures" / "sklavenitis" / "listing-page1.html"
)
SCRAPED_AT = datetime(2026, 5, 25, 12, 0, 0, tzinfo=timezone.utc)


def _load_offers() -> list[OfferItem]:
    return list(extract_offers(FIXTURE.read_text(encoding="utf-8"), SCRAPED_AT))


def test_extracts_one_offer_per_card() -> None:
    """The page has 24 product cards. Parser must emit one OfferItem per
    card."""
    offers = _load_offers()
    assert len(offers) == 24, f"expected 24 offers, got {len(offers)}"


def test_first_offer_field_mapping() -> None:
    """End-to-end map of the first card (KORPI mineral water 6x1.5lt, €1.65)."""
    offer = _load_offers()[0]

    assert offer.name == "ΚΟΡΠΗ Φυσικό Μεταλλικό Νερό 6x1,5lt"
    assert offer.external_id == "4569497"
    assert offer.price == Decimal("1.65")
    assert offer.currency == "EUR"
    assert offer.unit == "τεμ."

    # Category mapped from analytics blob.
    assert offer.category == "Φυσικά Μεταλλικά & Επιτραπέζια νερά"

    # Absolute URLs only.
    assert offer.url is not None
    assert offer.url.startswith("https://www.sklavenitis.gr/")
    assert "korp" in offer.url.lower()

    assert offer.image_url is not None
    assert offer.image_url.startswith("https://")
    assert "4569497" in offer.image_url

    # The listing doesn't expose original price / discount % — we emit
    # nulls rather than guess.
    assert offer.original_price is None
    assert offer.discount_pct is None


def test_offers_have_distinct_skus() -> None:
    """Each card carries its own SKU; the parser dedupes any rendering
    duplication."""
    offers = _load_offers()
    ids = [o.external_id for o in offers if o.external_id]
    assert len(ids) == 24
    assert len(set(ids)) == len(ids), "duplicate SKUs leaked through"


def test_units_are_greek_short_forms() -> None:
    """Sklavenitis uses ``τεμ.`` (each) and ``συσκ.`` (pack) on the offers
    page — both should survive the parse cleanly."""
    offers = _load_offers()
    units = {o.unit for o in offers if o.unit}
    assert units, "expected unit on every card"
    assert units <= {"τεμ.", "συσκ."}, f"unexpected units: {units}"


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
        assert key in payload
    # Decimal serialises as float for the JSON wire shape.
    assert payload["price"] == 1.65
    assert payload["original_price"] is None
    assert payload["discount_pct"] is None
    assert payload["scraped_at"].endswith("Z")
