# ADR 0002 — Parser test helpers

## Context

The five per-brand parser tests
(`test_{ab,lidl,masoutis,mymarket,sklavenitis}_parser.py`) all begin
with the same three-line boilerplate:

    FIXTURE = Path(__file__).parent / "fixtures" / "<brand>" / "<file>"
    SCRAPED_AT = datetime(2026, 5, 25, 12, 0, 0, tzinfo=UTC)
    def _load_offers() -> list[OfferItem]:
        return list(extract_offers(FIXTURE.read_text(encoding="utf-8"), SCRAPED_AT))

…and every file has a `test_payload_round_trip_matches_backend_contract`
which inlines the same 12-key list verifying `OfferItem.to_payload()`
keeps the wire contract. That's five copies of the wire contract.
Five places to update if the contract ever grows a column.

## Decision

Introduce `tests/_fixtures.py` exposing:

- `SCRAPED_AT` — the canonical fixture timestamp.
- `load_offers(brand_slug, fixture_filename)` — loads the fixture text,
  dispatches through `scraper.parsers.PARSERS[brand_slug]`, returns
  `list[OfferItem]`.
- `BACKEND_PAYLOAD_KEYS` — the wire contract's keyset, defined once.
- `assert_payload_matches_backend_contract(offer)` — assertion helper
  that every parser test calls instead of inlining the key list.

The module is a test-support helper (underscore-prefixed) and not part
of the public `scraper.*` API. The five parser tests adopt it; their
domain-specific assertions (Greek titles, exact prices, family mix,
…) stay untouched — only the boilerplate moves.

## Trade-offs

- **Cost**: one new test-support module (~40 lines). Tests now have an
  indirection layer between fixture path and call site — readers must
  jump to `_fixtures.py` to see the wire shape. Mitigated by a tight
  docstring there.
- **Benefit**: the wire contract has one source of truth in tests.
  When `OfferItem.to_payload()` grows a column, one test-helper update
  fans out to all five tests. Adding a 6th brand: one fixture file
  + one parser + one registry entry; the test pattern is reusable as
  is via `load_offers("<brand>", "<file>")`.
- **Not done**: no parametrised mega-test. Per-brand assertions live
  in per-brand files because the domain knowledge (Greek titles, AB
  family mix, Lidl rollover behaviour) is brand-specific.
