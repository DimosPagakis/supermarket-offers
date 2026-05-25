"""Tests for `variant_tokens` and `canonical_key`."""

from __future__ import annotations

from scraper.canonical.extractors import (
    canonical_key,
    canonical_size,
    extract_manufacturer,
    pack_count,
    variant_tokens,
)


def _features(name: str):
    """Helper: compute (variant_tokens, canonical_key) for a name."""
    m = extract_manufacturer(name)
    s = canonical_size(name)
    p = pack_count(name)
    v = variant_tokens(name, m, s)
    k = canonical_key(m, s, p, v) if m else None
    return m, s, p, v, k


# --- Variant tokens ---------------------------------------------------------

def test_brand_size_pack_stripped_from_tokens() -> None:
    _, _, _, v, _ = _features("Coca-Cola 6x330ml")
    # brand, '6', 'x', '330', 'ml' all removed
    assert v == frozenset(), v


def test_variant_tokens_preserve_flavour() -> None:
    _, _, _, v, _ = _features("Nirvana Παγωτό Cookie Dough 313γρ./420ml.")
    # Greek 'παγωτό' folded → 'pagoto'; English 'cookie', 'dough' preserved.
    assert "cookie" in v
    assert "dough" in v


def test_variant_tokens_dont_include_brand() -> None:
    _, _, _, v, _ = _features("MELISSA Σπαγγέτι Χωρίς γλουτένη 400g")
    assert "melissa" not in v
    assert any("spagg" in t for t in v) or any("spag" in t for t in v)


# --- Canonical key ----------------------------------------------------------

def test_melissa_three_chains_identical_key() -> None:
    """The doc's Tier-1 example: Melissa Σπαγγέτι 400g across three
    chains must produce the same canonical_key."""
    keys = {
        _features("MELISSA Σπαγγέτι Χωρίς γλουτένη 400g")[4],
        _features("Melissa Σπαγγέτι Χωρίς Γλουτένη 400gr")[4],
        _features("Melissa Σπαγγέτι Χωρίς Γλουτένη 400γρ.")[4],
    }
    assert len(keys) == 1, keys
    assert None not in keys


def test_pepsi_three_chains_identical_key() -> None:
    keys = {
        _features("PEPSI Cola 1,5lt")[4],
        _features("Pepsi Cola 1,5lt")[4],
        _features("Pepsi Cola 1,5lt.")[4],
    }
    assert len(keys) == 1, keys


def test_rio_mare_three_chains_identical_key() -> None:
    keys = {
        _features("RIO MARE Τόνος σε Ελαιόλαδο 3x80g")[4],
        _features("Rio Mare Τόνος Σε Ελαιόλαδο 3x80gr")[4],
        _features("Rio Mare Τόνος Σε Ελαιόλαδο 3x80γρ.")[4],
    }
    assert len(keys) == 1, keys


def test_pampers_no6_vs_no7_different_keys() -> None:
    """The whole point of size-aware blocking: different diaper sizes
    must NEVER canonicalise together."""
    k6 = _features("PAMPERS Active Baby Pants Πάνες Βρακάκι Νο6 13-19kg 42τεμ")[4]
    k7 = _features("PAMPERS Active Baby Pants Πάνες Βρακάκι Νο7 17-25kg 38τεμ")[4]
    assert k6 != k7
    assert "6no" in k6
    assert "7no" in k7


def test_nirvana_flavours_different_keys() -> None:
    """Flavour variants of the same brand/size must produce distinct keys."""
    k1 = _features("Nirvana Παγωτό Pistachio Almond 313γρ./420ml.")[4]
    k2 = _features("Nirvana Παγωτό Cookie Dough 302γρ./420ml.")[4]
    k3 = _features("Nirvana Παγωτό Brownies & Salted Caramel 302γρ./420ml.")[4]
    assert len({k1, k2, k3}) == 3


def test_coca_cola_15l_vs_1l_different_keys() -> None:
    k1 = _features("PEPSI Cola 1,5lt")[4]
    k2 = _features("Pepsi Cola 1lt")[4]
    assert k1 != k2


def test_canonical_key_deterministic() -> None:
    """Same input must always produce the same key."""
    k1 = _features("RIO MARE Τόνος σε Ελαιόλαδο 3x80g")[4]
    k2 = _features("RIO MARE Τόνος σε Ελαιόλαδο 3x80g")[4]
    assert k1 == k2


def test_canonical_key_format() -> None:
    """Key shape: manufacturer:variant:size:pack."""
    k = canonical_key(
        "coca-cola", (1.5, "l"), 2, frozenset({"original"})
    )
    parts = k.split(":")
    assert parts[0] == "coca-cola"
    assert parts[1] == "original"
    assert parts[2] == "1.5l"
    assert parts[3] == "2"


def test_canonical_key_with_no_size_or_variant() -> None:
    k = canonical_key("lacta", None, 1, frozenset())
    assert k.startswith("lacta:")
    assert "nosize" in k
