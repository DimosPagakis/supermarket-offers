"""Tests for `pack_count` — multi-pack count extractor."""

from __future__ import annotations

import pytest

from scraper.canonical.extractors import pack_count

# (name, expected_pack)
PACK_CASES: list[tuple[str, int]] = [
    ("Coca-Cola 2x1lt", 2),
    ("Lacta 3x28,5γρ", 3),
    ("RIO MARE Τόνος σε Ελαιόλαδο 3x80g", 3),
    ("Rio Mare Τόνος Σε Ελαιόλαδο 3x80gr", 3),
    ("Μπάρες Δημητριακών Cookies & Cream 6 X 23.5gr", 6),
    ("Μπάρες Δημητριακών Σοκολάτα Μπανάνα 6x23.5g", 6),
    ("Μπάρες Δημητριακών Cappuccino 4x23.5g", 4),
    ("Snickers Gold Παγωτό Ice Bar Multi 6x40,8γρ./51ml.", 6),
    ("Nescafe Dolce Gusto 16τεμ. 89,6γρ.", 1),  # τεμ is not a multi-pack
    ("ΙΟΝ Derby Σοκολάτα Classic 3x38g +1 Δώρο", 4),  # 3 + 1 free
    # +1 Δώρο on top of a 5-pack → effective 6 (matches the My Market 6x330ml)
    ("COCA-COLA Original Taste 5x330ml +1 Δώρο", 6),
    # Singles
    ("Coca-Cola 1,5lt", 1),
    ("Nirvana Παγωτό 420ml", 1),
    ("Pampers Νο6 42τεμ", 1),
    ("Empty", 1),
    ("", 1),
]


@pytest.mark.parametrize("name,expected", PACK_CASES)
def test_pack_count(name: str, expected: int) -> None:
    assert pack_count(name) == expected, name


def test_pack_cap_avoids_runaway() -> None:
    # We cap pack count at 48 to avoid '500g' becoming pack=500.
    # Sanity check: a non-pack string with random digits stays at 1.
    assert pack_count("SPF50 cream 200ml") == 1
