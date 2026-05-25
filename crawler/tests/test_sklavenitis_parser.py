"""Integration test for the Sklavenitis HTML listing parser.

Run against a committed snapshot of page 1 of
``/sylloges/prosfores/`` captured 2026-05-25 via ``curl_cffi`` (the
Akamai bot-manager rejects naive HTTP clients, see
``crawler/scraper/spiders/sklavenitis.py``).

The discounted-only emit gate (2026-05-25) drops the parser's output
to 1 / 24 cards on this fixture page — only the ``HEINEKEN 4+2 Δώρο``
card carries a real per-card promo signal. See module docstring on
``scraper/parsers/sklavenitis.py``. The brand is seeded
``active=false`` to match.
"""

from __future__ import annotations

from decimal import Decimal

from scraper.items import OfferItem

from ._fixtures import assert_payload_matches_backend_contract, load_offers


def _load_offers() -> list[OfferItem]:
    return load_offers("sklavenitis", "listing-page1.html")


def test_extracts_only_gift_badge_offers() -> None:
    """The page has 24 product cards but only 1 carries a real per-card
    promo signal (a ``.sign-badges`` "4+2 Δώρο" gift badge). The other
    23 are catalogue tiles and must be skipped silently."""
    offers = _load_offers()
    assert len(offers) == 1, f"expected 1 gift-badge offer, got {len(offers)}"


def test_gift_badge_offer_field_mapping() -> None:
    """End-to-end map of the lone discounted card (HEINEKEN 4+2 Δώρο)."""
    offer = _load_offers()[0]

    assert offer.name == "HEINEKEN Μπίρα Lager 4x330ml +2 Δώρο"
    assert offer.external_id == "1506011"
    assert offer.price == Decimal("5.27")
    assert offer.currency == "EUR"
    assert offer.unit == "τεμ."

    # Absolute URLs only.
    assert offer.url is not None
    assert offer.url.startswith("https://www.sklavenitis.gr/")

    assert offer.image_url is not None
    assert offer.image_url.startswith("https://")

    # No strikethrough / pct on the listing — we only synthesise the
    # gift-badge label and tag it as ``bxgy_free``.
    assert offer.original_price is None
    assert offer.discount_pct is None
    assert offer.promo_label == "4+2 Δώρο"
    assert offer.promo_type == "bxgy_free"


def test_offers_have_distinct_skus() -> None:
    """Each emitted card carries its own SKU."""
    offers = _load_offers()
    ids = [o.external_id for o in offers if o.external_id]
    assert len(ids) == len(set(ids)), "duplicate SKUs leaked through"


def test_payload_round_trip_matches_backend_contract() -> None:
    offer = _load_offers()[0]
    payload = assert_payload_matches_backend_contract(offer)
    # Decimal serialises as float for the JSON wire shape.
    assert payload["price"] == 5.27
    assert payload["original_price"] is None
    assert payload["discount_pct"] is None
    assert payload["promo_label"] == "4+2 Δώρο"
    assert payload["promo_type"] == "bxgy_free"
    assert payload["scraped_at"].endswith("Z")
