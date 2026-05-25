"""Shared test-support helpers for the per-brand parser test suites.

The five per-brand parser tests all share three pieces of boilerplate:

* a ``FIXTURE`` path under ``tests/fixtures/<brand>/<file>``,
* a frozen ``SCRAPED_AT`` so date-bearing fields don't drift,
* a ``_load_offers()`` shim that reads the fixture and runs it through
  the brand's ``extract_offers``.

…plus a ``test_payload_round_trip_matches_backend_contract`` that
inlines the 12-key wire contract verbatim.

This module centralises both. Test files keep their domain-specific
assertions (Greek titles, AB family mix, Lidl rollover behaviour) and
delegate the boilerplate here. See ADR 0002.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from scraper.items import OfferItem
from scraper.parsers import PARSERS

#: Canonical timestamp used by every parser fixture test. Frozen at the
#: capture date so the ``scraped_at`` field in fixtures stays stable.
SCRAPED_AT = datetime(2026, 5, 25, 12, 0, 0, tzinfo=UTC)


#: Root of the committed parser fixtures. Per-brand subdirectories live
#: directly under this path (``ab/``, ``lidl/``, ``masoutis/``,
#: ``mymarket/``, ``sklavenitis/``).
FIXTURES_ROOT = Path(__file__).parent / "fixtures"


#: Brand-slug → fixture-subdirectory mapping. Most slugs match the
#: directory name, but the My Market spider's slug ``my-market`` is
#: hyphenated while the fixtures live under ``mymarket/`` (one word).
#: The committed fixtures are frozen, so the mapping lives here.
_FIXTURE_DIRS: dict[str, str] = {
    "ab": "ab",
    "lidl": "lidl",
    "masoutis": "masoutis",
    "my-market": "mymarket",
    "sklavenitis": "sklavenitis",
}


#: The set of keys the backend's bulk-upsert endpoint validates against.
#: ``OfferItem.to_payload()`` is the single source of truth for the wire
#: shape; this list is its mirror in the test suite, asserted by
#: :func:`assert_payload_matches_backend_contract` for every brand.
BACKEND_PAYLOAD_KEYS: frozenset[str] = frozenset({
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
})


def fixture_path(brand_slug: str, filename: str) -> Path:
    """Resolve a fixture path under ``tests/fixtures/<dir>/<filename>``.

    The directory is looked up via :data:`_FIXTURE_DIRS` so callers pass
    the runtime brand slug (e.g. ``my-market``) and the helper resolves
    it to the committed fixture directory (``mymarket``).
    """
    return FIXTURES_ROOT / _FIXTURE_DIRS[brand_slug] / filename


def load_offers(brand_slug: str, filename: str) -> list[OfferItem]:
    """Load ``tests/fixtures/<brand>/<filename>`` and return the parsed offers.

    Dispatches through :data:`scraper.parsers.PARSERS` so the same brand
    slug used at runtime selects the parser. ``brand_slug`` matches the
    spider's ``name`` attribute (e.g. ``"my-market"``, not ``"mymarket"``).
    """
    parser = PARSERS[brand_slug]
    raw = fixture_path(brand_slug, filename).read_text(encoding="utf-8")
    return list(parser(raw, SCRAPED_AT))


def assert_payload_matches_backend_contract(offer: OfferItem) -> dict:
    """Round-trip ``offer`` through ``to_payload()`` and assert it carries
    the full backend wire contract. Returns the payload so callers can
    add brand-specific value checks (e.g. ``payload["price"] == 6.08``)
    on top.
    """
    payload = offer.to_payload()
    missing = BACKEND_PAYLOAD_KEYS - payload.keys()
    assert not missing, f"missing keys in offer payload: {sorted(missing)}"
    return payload
