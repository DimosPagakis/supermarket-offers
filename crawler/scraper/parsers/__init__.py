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
"""
