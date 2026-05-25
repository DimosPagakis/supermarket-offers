"""Per-brand HTML/JSON-to-OfferItem parsers.

Kept dependency-free of Scrapy so they can be exercised against saved
fixtures in plain pytest. Spiders are thin shells that call into here.

Naming convention
-----------------
Every parser exposes::

    extract_offers(raw: str, scraped_at: datetime) -> Iterable[OfferItem]

…which is the entry point the spiders consume. ``raw`` is HTML for the
HTML-listing brands (Lidl, My Market, Sklavenitis) and a JSON-encoded
response body for the API-driven brands (AB, Masoutis).

The two JSON brands additionally expose a sibling
``extract_offers_from_payload(payload, scraped_at)`` so callers that
already hold a parsed dict / list can skip the ``json.loads`` round
trip — the Masoutis spider, which reads bodies straight off Playwright,
uses that variant. AB also exposes ``extract_offers_with_family`` for
the spider's per-promotion-family histogram.

Programmatic access
-------------------
The :data:`PARSERS` dict maps a brand slug to its ``extract_offers``
callable. This is the canonical "slug → parser" lookup used by the
test fixture helper; spiders import the per-brand function directly
because the slug is fixed at module import time. Adding a 6th brand
means writing the parser module and adding one entry below.

The :class:`OfferParser` ``Protocol`` documents the parser shape so a
future parser whose signature drifts breaks mypy rather than passing
silently. It is structural — existing module-level functions match it
without any import-side change.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from typing import Protocol

from scraper.items import OfferItem

from . import ab, lidl, masoutis, mymarket, sklavenitis


class OfferParser(Protocol):
    """Structural type for the per-brand parser entry point.

    Every ``scraper.parsers.<brand>.extract_offers`` satisfies this
    Protocol by construction — there is no need to import or inherit
    from it inside the parser modules.
    """

    def __call__(
        self, raw_text: str, scraped_at: datetime
    ) -> Iterable[OfferItem]: ...


# Brand slug → parser entry point. Slugs match the seeded backend
# ``brands.slug`` column and the per-spider ``name`` attribute.
PARSERS: dict[str, OfferParser] = {
    "ab": ab.extract_offers,
    "lidl": lidl.extract_offers,
    "masoutis": masoutis.extract_offers,
    "my-market": mymarket.extract_offers,
    "sklavenitis": sklavenitis.extract_offers,
}


__all__ = ["OfferParser", "PARSERS"]
