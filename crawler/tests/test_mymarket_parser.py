"""Integration test for the My Market HTML listing parser.

Run against a committed snapshot of page 1 of ``/offers`` captured
2026-05-25.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from scraper.items import OfferItem
from scraper.parsers.mymarket import extract_offers

FIXTURE = (
    Path(__file__).parent / "fixtures" / "mymarket" / "listing-page1.html"
)
SCRAPED_AT = datetime(2026, 5, 25, 12, 0, 0, tzinfo=timezone.utc)


def _load_offers() -> list[OfferItem]:
    return list(extract_offers(FIXTURE.read_text(encoding="utf-8"), SCRAPED_AT))


def test_extracts_one_offer_per_card() -> None:
    """The page has 35 ``.product--teaser`` cards. Parser must emit one
    OfferItem per card with a parseable price."""
    offers = _load_offers()
    assert len(offers) == 35, f"expected 35 offers, got {len(offers)}"


def test_first_offer_field_mapping() -> None:
    """End-to-end map of the first card (Greek carrots, €0.72)."""
    offer = _load_offers()[0]

    assert offer.name == "Καρότα Ελληνικά Τιμή Κιλού"
    assert offer.external_id == "192321"  # from analytics JSON; data-id is 11625
    assert offer.price == Decimal("0.72")

    # The page doesn't expose original price / discount % on the listing
    # view — we explicitly emit nulls rather than guess.
    assert offer.original_price is None
    assert offer.discount_pct is None

    # Currency is hardcoded EUR (the page is Greek-market-only).
    assert offer.currency == "EUR"

    # Category comes from the analytics blob's deepest level.
    assert offer.category is not None and "Καρότα" in offer.category

    # URL is the absolute product page.
    assert offer.url == "https://www.mymarket.gr/karota-ellinika-timi-kilou"

    # Image absolute URL.
    assert offer.image_url is not None
    assert offer.image_url.startswith("https://cdn.mymarket.gr/images/")


def test_offers_dedupe_within_page() -> None:
    """My Market renders each card with two analytics-tagged anchors per
    card (header tooltip + image). The parser must still emit one offer
    per data-id."""
    offers = _load_offers()
    ids = [o.external_id for o in offers if o.external_id]
    assert len(ids) == len(set(ids)), "duplicate external_ids leaked through"


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
    assert payload["price"] == 0.72
    assert payload["original_price"] is None
    assert payload["discount_pct"] is None
