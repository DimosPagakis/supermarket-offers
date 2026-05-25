"""Tests for the rule-based matcher."""

from __future__ import annotations

from scraper.canonical.extractors import extract_features
from scraper.canonical.matcher import match_decision


def _f(pid: int, brand: str, name: str):
    return extract_features(pid, brand, name)


def test_different_brand_not_same() -> None:
    a = _f(1, "sklavenitis", "LACTA Σοκολάτα 85g")
    b = _f(2, "my-market", "MILKA Σοκολάτα 85g")
    d = match_decision(a, b)
    assert d.same is False
    assert "brand" in d.reason


def test_different_size_not_same() -> None:
    a = _f(1, "sklavenitis", "Coca-Cola 1lt")
    b = _f(2, "my-market", "Coca-Cola 1,5lt")
    d = match_decision(a, b)
    assert d.same is False
    assert "size" in d.reason


def test_different_pack_not_same() -> None:
    a = _f(1, "sklavenitis", "Coca-Cola 2x1lt")
    b = _f(2, "my-market", "Coca-Cola 6x1lt")
    d = match_decision(a, b)
    assert d.same is False
    assert "pack" in d.reason


def test_pampers_no6_vs_no7_not_same() -> None:
    a = _f(1, "sklavenitis", "PAMPERS Active Baby Pants Πάνες Βρακάκι Νο6 13-19kg 42τεμ")
    b = _f(2, "masoutis", "PAMPERS Active Baby Pants Πάνες Βρακάκι Νο7 17-25kg 38τεμ")
    d = match_decision(a, b)
    assert d.same is False


def test_melissa_match_across_chains() -> None:
    a = _f(1, "sklavenitis", "MELISSA Σπαγγέτι Χωρίς γλουτένη 400g")
    b = _f(2, "my-market", "Melissa Σπαγγέτι Χωρίς Γλουτένη 400gr")
    c = _f(3, "masoutis", "Melissa Σπαγγέτι Χωρίς Γλουτένη 400γρ.")
    assert match_decision(a, b).same is True
    assert match_decision(a, c).same is True
    assert match_decision(b, c).same is True


def test_unknown_manufacturer_never_merges() -> None:
    """Two own-brand products that happen to look identical must not merge."""
    a = _f(1, "ab", "Δημητριακά Ολικής Άλεσης 325g")
    b = _f(2, "my-market", "Δημητριακά Ολικής Άλεσης 325g")
    d = match_decision(a, b)
    assert d.same is False
    assert "manufacturer" in d.reason


def test_nirvana_flavour_mismatch_not_same() -> None:
    a = _f(1, "sklavenitis", "Nirvana Παγωτό Pistachio Almond 313γρ./420ml.")
    b = _f(2, "masoutis", "Nirvana Παγωτό Cookie Dough 302γρ./420ml.")
    d = match_decision(a, b)
    assert d.same is False
    # Same brand/size/pack, only variants differ — should hit the
    # variant-mismatch branch, not the brand/size/pack branches.
    assert "variant" in d.reason.lower() or "jaccard" in d.reason.lower()


def test_disjoint_variant_tokens_reject_with_full_confidence() -> None:
    """Phase 2.1 regression: when two products share brand+size+pack but
    their variant token sets are non-empty and *disjoint*, the matcher
    must REJECT with confidence 1.0 — not produce the old ambiguous 0.6
    that leaks into the embedding fallback band and over-merges
    boilerplate-heavy families (Axe deodorants, Ariel pods, …)."""
    a = _f(1, "sklavenitis", "Nirvana Vanilla 420ml")
    b = _f(2, "masoutis", "Nirvana Strawberry 420ml")
    # Sanity: same brand+size+pack (the block key), disjoint variant
    # tokens after boilerplate stripping. The fixture only holds if the
    # extractor keeps "vanilla" / "strawberry" as the discriminator.
    assert a.manufacturer == b.manufacturer
    assert a.size == b.size
    assert a.pack == b.pack
    assert a.variant_tokens and b.variant_tokens
    assert not (a.variant_tokens & b.variant_tokens), (
        f"fixture invalid — token sets must be disjoint, got "
        f"{a.variant_tokens} vs {b.variant_tokens}"
    )

    d = match_decision(a, b)
    assert d.same is False
    assert d.confidence == 1.0
    assert "disjoint" in d.reason.lower()
    assert d.method == "rule"


def test_base_sku_with_empty_variant_matches() -> None:
    """When both products strip down to nothing (same brand+size+pack and
    no descriptors), we treat them as a confident match."""
    a = _f(1, "sklavenitis", "Coca-Cola 6x330ml")
    b = _f(2, "my-market", "Coca-Cola 6x330ml")
    d = match_decision(a, b)
    assert d.same is True
    assert d.confidence >= 0.9
