"""Integration test for the My Market HTML listing parser.

Run against a committed snapshot of page 1 of ``/offers`` captured
2026-05-25.
"""

from __future__ import annotations

from decimal import Decimal

from scraper.items import OfferItem
from scraper.parsers.mymarket import extract_offers, extract_total_pages

from ._fixtures import (
    SCRAPED_AT,
    assert_payload_matches_backend_contract,
    fixture_path,
    load_offers,
)

FIXTURE = fixture_path("my-market", "listing-page1.html")


def _load_offers() -> list[OfferItem]:
    return load_offers("my-market", "listing-page1.html")


def test_extracts_only_discounted_offers() -> None:
    """The page has 35 ``.product--teaser`` cards but ``/offers`` is the
    entire chain catalogue, not a real flyer. The parser gates emit on
    a ``diagonal-line`` strikethrough or an explicit ``offer-note--percent``
    pill — cards carrying only the "SUPER ΤΙΜΗ" everyday-low-price
    sticker are skipped silently. Net expected: 7 real discounted
    offers (5 ΠΡΟΣΦΟΡΑ + 2 -N%)."""
    offers = _load_offers()
    assert len(offers) == 7, f"expected 7 discounted offers, got {len(offers)}"
    # Every emitted offer must carry a real promo signal — that is the
    # whole point of the gate.
    for o in offers:
        assert o.promo_label is not None
        assert o.promo_type == "strikethrough"


def test_percent_pill_card_maps_discount_pct_and_label() -> None:
    """A card with a "-25%" pill must surface ``discount_pct=25`` and a
    "−25%" promo label so the FE renders the brand-supplied discount
    figure verbatim."""
    offer = next(o for o in _load_offers() if o.external_id == "118918")
    assert offer.name.startswith("Ροδόπη Γιαούρτι")
    assert offer.price == Decimal("1.04")
    assert offer.discount_pct == 25
    assert offer.promo_label == "−25%"
    assert offer.promo_type == "strikethrough"
    # Currency is hardcoded EUR (the page is Greek-market-only).
    assert offer.currency == "EUR"


def test_prosfora_only_card_emits_generic_label() -> None:
    """A card with a ``diagonal-line`` strikethrough but no "-N%" pill
    (Discount text lives only on the comparator price) still emits with
    a ``ΠΡΟΣΦΟΡΑ`` promo label — required by the backend's defensive
    promo-signal validator and rendered on the FE as the brand-supplied
    badge."""
    offer = next(o for o in _load_offers() if o.external_id == "134061")
    assert offer.name.startswith("Χοιρινός Λαιμός")
    assert offer.price == Decimal("5.29")
    assert offer.discount_pct is None
    assert offer.promo_label == "ΠΡΟΣΦΟΡΑ"
    assert offer.promo_type == "strikethrough"


def test_offers_dedupe_within_page() -> None:
    """My Market renders each card with two analytics-tagged anchors per
    card (header tooltip + image). The parser must still emit one offer
    per data-id."""
    offers = _load_offers()
    ids = [o.external_id for o in offers if o.external_id]
    assert len(ids) == len(set(ids)), "duplicate external_ids leaked through"


def test_payload_round_trip_matches_backend_contract() -> None:
    offer = next(o for o in _load_offers() if o.external_id == "118918")
    payload = assert_payload_matches_backend_contract(offer)
    assert payload["price"] == 1.04
    assert payload["original_price"] is None
    assert payload["discount_pct"] == 25
    assert payload["promo_label"] == "−25%"
    assert payload["promo_type"] == "strikethrough"


def test_extract_total_pages_from_listing() -> None:
    """The fixture's pagination nav exposes ``data-mkey="page-159"`` as
    the highest page link. The parser should pick that up so the spider
    knows how far to walk."""
    html = FIXTURE.read_text(encoding="utf-8")
    assert extract_total_pages(html) == 159


def test_extract_total_pages_returns_none_without_pagination() -> None:
    """If the listing has no pagination nav at all (single-page result),
    the parser should return ``None`` so the spider can treat it as a
    one-page crawl rather than misclassify selector drift as 'no more
    pages'."""
    html_no_nav = """
    <html><body>
      <div class="product--teaser" data-id="1">...</div>
    </body></html>
    """
    assert extract_total_pages(html_no_nav) is None


def test_extract_offers_returns_empty_on_zero_card_page() -> None:
    """Defence-in-depth pagination stop signal: if a page has no
    ``.product--teaser`` cards (catalogue end / selector drift), the
    parser should yield nothing rather than raising. The spider relies
    on that to short-circuit pagination safely."""
    html_no_cards = """
    <html><body>
      <main>
        <h1>No offers found</h1>
        <nav><a data-mkey="page-2" href="/offers?page=2">2</a></nav>
      </main>
    </body></html>
    """
    offers = list(
        extract_offers(html_no_cards, SCRAPED_AT)
    )
    assert offers == []
