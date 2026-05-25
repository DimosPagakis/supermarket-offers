# ADR 0001 — `OfferParser` Protocol

## Context

All five brand parsers share the same shape:

    extract_offers(raw_text: str, scraped_at: datetime) -> Iterable[OfferItem]

The contract is documented in `scraper/parsers/__init__.py` but enforced
only by convention — five duck-typed call sites in spiders, five copies
of the same shape in tests, no type-checker support, no programmatic
way to enumerate "which parser handles which brand".

A 6th brand will repeat the same pattern. The parser test files repeat
the same `_load_offers()` boilerplate — see ADR 0002.

## Decision

Introduce a single `OfferParser` `typing.Protocol` in
`scraper/parsers/__init__.py` and a `PARSERS` dict mapping brand slug
to its parser callable. The protocol is structural — existing module-
level `extract_offers` functions match it as-is, no refactor needed
inside per-brand parser modules. The dict centralises the
"slug → parser" relationship that today is implicit in each spider's
import line.

## Trade-offs

- **Cost**: one new symbol (`OfferParser`) plus a small dict (`PARSERS`).
  Adds one mypy-checked seam where there was none. No runtime cost.
- **Benefit**: enables the generic fixture helper in ADR 0002 (one
  call site that picks the parser by slug); type-checker will catch
  a future parser whose signature drifts; adding a 6th brand becomes
  "write parser, register in `PARSERS`".
- **Not done**: no ABC, no per-parser class. Module-level functions
  stay. The Protocol is structural, so the parsers don't even import
  it — only callers do.
