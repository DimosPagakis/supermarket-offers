"""Integration test for the Lidl listing parser.

Run against a committed snapshot of a real listing page
(``tests/fixtures/lidl/listing.html`` — captured 2026-05-25 from
``/c/evdomadiaies-epiloges-26kw22/a10095458``). This is exactly the
flavour of test the crawler CLAUDE.md asks for: selector / schema
drift detection against frozen HTML, no live network.

If Lidl reshapes the ``data-grid-data`` JSON, these assertions break
loudly and we tune the parser before shipping.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from scraper.items import OfferItem

from ._fixtures import assert_payload_matches_backend_contract, load_offers

# The "current" fixture was captured live on 2026-05-25 from the same
# campaign URL (``/c/evdomadiaies-epiloges-26kw22/a10095458``) *after*
# Lidl flipped the active offers from ``futurePrices`` to ``currentPrice``.
# Both fixtures must parse — see ``_pick_price_block`` in
# scraper/parsers/lidl.py.


def _load_offers() -> list[OfferItem]:
    return load_offers("lidl", "listing.html")


def _load_offers_current() -> list[OfferItem]:
    return load_offers("lidl", "listing_current.html")


def test_extracts_priced_offers_only() -> None:
    """The fixture has 27 grid cards. Five of them carry no current sale
    price and must be skipped silently:
      * 3 with an entirely empty ``regionsPrices`` (online-only / banner
        wrappers),
      * 2 with ``regionsPrices.1`` present but ``futurePrices == []``
        (RETAIL products without a current promotion).
    Net expected: 22 priced offers."""
    offers = _load_offers()
    assert len(offers) == 22, f"expected 22 priced offers, got {len(offers)}"


def test_first_offer_maps_all_critical_fields() -> None:
    """Smoke-check the first offer end-to-end against known fixture values."""
    offers = _load_offers()
    first = offers[0]

    # Greek title preserved (no transliteration, no whitespace damage).
    assert first.name == "Χαρτί κουζίνας 3πλα φύλλα"

    # Lidl productId becomes external_id as a string.
    assert first.external_id == "11022981"

    # Sale + original price decoded as Decimal with the right scale.
    assert first.price == Decimal("2.29")
    assert first.original_price == Decimal("3.29")
    assert first.discount_pct == 30

    # Currency preserved from JSON, not hardcoded.
    assert first.currency == "EUR"

    # Validity dates parsed from ISO timestamps.
    assert first.valid_from == date(2026, 5, 27)
    assert first.valid_to == date(2026, 6, 3)

    # Canonical URL becomes an absolute Lidl URL.
    assert first.url is not None
    assert first.url.startswith("https://www.lidl-hellas.gr/p/")
    assert "p11022981" in first.url

    # First image from imageList_V1.
    assert first.image_url is not None
    assert first.image_url.startswith("https://www.lidl-hellas.gr/assets/")

    # Packaging string lands in `unit`.
    assert first.unit == "208 φύλλα (720 g)"

    # Lidl exposes single-unit discounts only — we synthesise a
    # "−{N}%" label and tag the row as `strikethrough` so the FE pill
    # gets to render the brand-supplied savings copy.
    assert first.promo_type == "strikethrough"
    assert first.promo_label == "−30%"


def test_handles_offer_without_discount_block() -> None:
    """Item #2 in the fixture (Κοπανάκι κοτόπουλο XXL) has a price but no
    oldPrice / percentageDiscount. Parser should keep the offer and just
    omit the optional fields."""
    offers = _load_offers()

    target = next((o for o in offers if o.external_id == "11529991"), None)
    assert target is not None, "expected to find productId 11529991"
    assert target.name.strip().startswith("Κοπανάκι κοτόπουλο")
    assert target.price == Decimal("4.49")
    assert target.original_price is None
    assert target.discount_pct is None
    # No discount block → neither field is populated either.
    assert target.promo_label is None
    assert target.promo_type is None


def test_offers_are_deduplicated_by_external_id() -> None:
    """Lidl occasionally renders the same product in multiple grid sections
    on one page. The parser dedupes within a single document."""
    offers = _load_offers()
    ids = [o.external_id for o in offers if o.external_id]
    assert len(ids) == len(set(ids)), "duplicate external_ids leaked through"


def test_payload_is_backend_contract_shaped() -> None:
    """Round-trip through OfferItem.to_payload() so the contract with
    POST /api/v1/crawl-runs/{run}/offers stays exercised end-to-end in
    the parser test, not just the API client unit test."""
    offers = _load_offers()
    payload = assert_payload_matches_backend_contract(offers[0])

    # Numeric fields are serialized as JSON-friendly floats / ints.
    assert isinstance(payload["price"], float)
    assert isinstance(payload["discount_pct"], int)
    # Dates serialized as ISO strings.
    assert payload["valid_from"] == "2026-05-27"
    assert payload["valid_to"] == "2026-06-03"


# --------------------------------------------------------------------------
# Regression: ``currentPrice`` shape (2026-05-25 schema drift)
# --------------------------------------------------------------------------
#
# After the Thursday rollover, Lidl moves a now-live offer's price block
# from ``regionsPrices.<region>.futurePrices[0].price`` into a sibling
# ``regionsPrices.<region>.currentPrice`` dict (identical inner shape).
# The parser used to look only at ``futurePrices`` and silently dropped
# the entire current-week catalogue once the rollover hit — observed live
# on 2026-05-25 as a collapse from ~85 priced offers to ~27. The cases
# below pin the fix.


def test_extracts_priced_offers_from_currentPrice_shape() -> None:
    """The currentPrice fixture has 26 grid cards. 23 carry a live
    ``currentPrice`` block, 3 are unpriced wrappers (empty regionsPrices)
    and must be skipped silently. Net expected: 23 priced offers."""
    offers = _load_offers_current()
    assert len(offers) == 23, f"expected 23 priced offers, got {len(offers)}"


def test_currentPrice_first_offer_maps_all_critical_fields() -> None:
    """End-to-end mapping check against the currentPrice fixture. Same
    productId (11022981) as the futurePrices fixture so we know the inner
    schema is identical regardless of which sibling key wraps it."""
    offers = _load_offers_current()
    first = offers[0]

    assert first.name == "Χαρτί κουζίνας 3πλα φύλλα"
    assert first.external_id == "11022981"
    assert first.price == Decimal("2.29")
    assert first.original_price == Decimal("3.29")
    assert first.discount_pct == 30
    assert first.currency == "EUR"
    # currentPrice carries a startDate of "now-ish" (the moment Lidl
    # flipped the promo live) and an endDate matching the campaign end.
    # We only assert the campaign-end date since the start moves around.
    assert first.valid_to == date(2026, 6, 3)
    assert first.url is not None and "p11022981" in first.url
    assert first.unit == "208 φύλλα (720 g)"


def test_currentPrice_offers_have_no_duplicate_external_ids() -> None:
    """Dedupe must still work after switching to the currentPrice shape."""
    offers = _load_offers_current()
    ids = [o.external_id for o in offers if o.external_id]
    assert len(ids) == len(set(ids)), "duplicate external_ids leaked through"
