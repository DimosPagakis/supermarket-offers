"""Tests for `canonical_size` against real names from :8001."""

from __future__ import annotations

import pytest

from scraper.canonical.extractors import canonical_size

# (raw_name, expected (value, unit))
GRAM_CASES: list[tuple[str, tuple[float, str]]] = [
    ("LACTA Nuts Σοκολάτα 85g", (85.0, "g")),
    ("MELISSA Σπαγγέτι Χωρίς γλουτένη 400g", (400.0, "g")),
    ("Melissa Σπαγγέτι Χωρίς Γλουτένη 400gr", (400.0, "g")),
    ("Melissa Σπαγγέτι Χωρίς Γλουτένη 400γρ.", (400.0, "g")),
    ("Lacta Γκοφρέτα 28,5γρ", (28.5, "g")),
    ("Snack Σκύλων Denta Stix 77g", (77.0, "g")),
    ("HEINZ Κέτσαπ Βιολογική 580g", (580.0, "g")),
    ("LURPAK Βούτυρο Ελαφρώς Αλατισμένο 200g", (200.0, "g")),
]

LITRE_CASES: list[tuple[str, tuple[float, str]]] = [
    ("AJAX Καθαριστικό Πατώματος Vegan 1lt", (1.0, "l")),
    ("Coca Cola 2x1lt.", (1.0, "l")),
    ("PEPSI Cola 1,5lt", (1.5, "l")),
    ("Pepsi Cola 1,5lt.", (1.5, "l")),
]

MILLILITRE_CASES: list[tuple[str, tuple[float, str]]] = [
    # Volume wins over weight when both appear (Nirvana ice cream).
    ("Nirvana Παγωτό Pistachio Almond 313γρ./420ml.", (420.0, "ml")),
    ("Nirvana Παγωτό Brownies & Salted Caramel 302γρ/420ml.", (420.0, "ml")),
    ("Coca-Cola 6x330ml", (330.0, "ml")),
    ("COCA-COLA Original Taste 5x330ml +1 Δώρο", (330.0, "ml")),
    ("Nivea Sun Αντηλιακό 200ml", (200.0, "ml")),
    ("Soflan Bivalent 24mez. 960ml.", (960.0, "ml")),
    ("LACTACYD Fresh Λοσιόν 200ml", (200.0, "ml")),
]

DESIGNATOR_CASES: list[tuple[str, tuple[float, str]]] = [
    # Diaper / pasta `No` designator — wins over weight & pack.
    ("PAMPERS Active Baby Pants Πάνες Βρακάκι Νο6 13-19kg 42τεμ", (6.0, "no")),
    ("PAMPERS Active Baby Pants Πάνες Βρακάκι Νο7 17-25kg 38τεμ", (7.0, "no")),
    ("Μακαρόνια Σπαγγέτι Νο5 500g", (5.0, "no")),
    ("Tortiglioni Νο 83 500gr", (83.0, "no")),
    ("EXCELLENCE Creme Βαφή Μαλλιών No7 Ξανθό 48ml", (7.0, "no")),
]

PIECE_CASES: list[tuple[str, tuple[float, str]]] = [
    ("Βούρτσα Μαλλιών Οβάλ 1 Τεμάχιο", (1.0, "τεμ")),
    ("K2R Colour Catcher Χρωμοπαγίδα 40 φύλλα", (40.0, "τεμ")),
]

NONE_CASES: list[str] = [
    "",
    "   ",
    "Some name without size",
]


@pytest.mark.parametrize("name,expected", GRAM_CASES)
def test_gram_sizes(name: str, expected: tuple[float, str]) -> None:
    assert canonical_size(name) == expected


@pytest.mark.parametrize("name,expected", LITRE_CASES)
def test_litre_sizes(name: str, expected: tuple[float, str]) -> None:
    assert canonical_size(name) == expected


@pytest.mark.parametrize("name,expected", MILLILITRE_CASES)
def test_ml_sizes(name: str, expected: tuple[float, str]) -> None:
    assert canonical_size(name) == expected


@pytest.mark.parametrize("name,expected", DESIGNATOR_CASES)
def test_designator_sizes(name: str, expected: tuple[float, str]) -> None:
    assert canonical_size(name) == expected


@pytest.mark.parametrize("name,expected", PIECE_CASES)
def test_piece_sizes(name: str, expected: tuple[float, str]) -> None:
    assert canonical_size(name) == expected


@pytest.mark.parametrize("name", NONE_CASES)
def test_no_size_returns_none(name: str) -> None:
    assert canonical_size(name) is None


def test_greek_decimal_comma() -> None:
    # Greek convention uses '1,5'. Our parser must treat it as 1.5.
    assert canonical_size("Vodka 1,5lt") == (1.5, "l")
    assert canonical_size("Lacta 28,5γρ") == (28.5, "g")


def test_designator_wins_over_pack_pieces() -> None:
    # Even though "42τεμ" is also a measure, the No designator must win
    # for the diaper SKU identity rule.
    v = canonical_size("PAMPERS Νο6 13-19kg 42τεμ")
    assert v == (6.0, "no")


def test_volume_wins_over_weight() -> None:
    # 313 grams AND 420 ml present — pick ml.
    v = canonical_size("Nirvana Παγωτό 313γρ./420ml.")
    assert v == (420.0, "ml")
