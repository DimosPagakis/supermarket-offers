"""Lock the ``scraper.parsers.PARSERS`` brand-slug → parser registry.

The registry is the documented seam used by the fixture helper and by
any future code that needs to dispatch to a parser by brand slug. This
test guards two invariants:

1. Every spider in ``scraper.spiders`` is represented — adding a 6th
   spider but forgetting to register the parser would silently break
   the generic test path.
2. Every registered callable is invocable with the parser shape
   (``raw_text``, ``scraped_at``) → some iterable. We don't exercise
   it against real data here — the per-brand parser tests already do.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime
from inspect import signature

from scraper.parsers import PARSERS


def test_registry_covers_every_spider() -> None:
    """Every spider name must appear as a key in ``PARSERS``."""
    from scraper.spiders import ab, lidl, masoutis, mymarket, sklavenitis

    spider_names = {
        ab.AbSpider.name,
        lidl.LidlSpider.name,
        masoutis.MasoutisSpider.name,
        mymarket.MyMarketSpider.name,
        sklavenitis.SklavenitisSpider.name,
    }
    assert set(PARSERS) == spider_names, (
        f"PARSERS keys {set(PARSERS)} do not match spider names {spider_names}"
    )


def test_every_parser_has_the_documented_signature() -> None:
    """Every registered parser must accept (raw_text, scraped_at)."""
    for slug, parser in PARSERS.items():
        sig = signature(parser)
        params = list(sig.parameters.values())
        # All five concrete parsers expose ``extract_offers(raw, scraped_at)``.
        assert len(params) == 2, (
            f"{slug}: expected 2-arg signature, got {len(params)} ({params})"
        )


def test_parsers_yield_iterable_on_empty_input() -> None:
    """Defensive: an empty / malformed input should yield zero offers
    (not raise). All five parsers already honour this in their per-brand
    tests; the registry test just confirms the empty-iterable contract
    holds across the dispatch path."""
    scraped_at = datetime(2026, 5, 25, 12, 0, 0, tzinfo=UTC)
    for slug, parser in PARSERS.items():
        # Pass a body that's syntactically valid but carries no offers.
        empty = "[]" if slug in {"ab", "masoutis"} else "<html></html>"
        out = parser(empty, scraped_at)
        assert isinstance(out, Iterable), f"{slug}: not an Iterable"
        # Materialise — should not raise.
        list(out)
