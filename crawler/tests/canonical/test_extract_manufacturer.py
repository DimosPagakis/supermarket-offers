"""Tests for `extract_manufacturer` against real names pulled from
:8001 on 2026-05-25. Every assertion below corresponds to a row that
actually exists in the live DB.
"""

from __future__ import annotations

import pytest

from scraper.canonical.extractors import extract_manufacturer

# (raw_name, expected_canonical_brand_or_None)
KNOWN_BRAND_CASES: list[tuple[str, str | None]] = [
    # National brands across chains — Sklavenitis uppercases, Masoutis
    # title-cases, My Market is mixed.
    ("LACTA Nuts Σοκολάτα Γάλακτος με Καραμελωμένο Αμύγδαλο 85g", "lacta"),
    ("Nirvana Παγωτό Pistachio Almond 313γρ./420ml.", "nirvana"),
    ("Nirvana Παγωτό Cookie Dough 302γρ./420ml.", "nirvana"),
    ("COCA-COLA Original Taste 5x330ml +1 Δώρο", "coca-cola"),
    ("Coca-Cola 6x330ml", "coca-cola"),
    ("Coca Cola 2x1lt.", "coca-cola"),
    ("PEPSI Cola 1,5lt", "pepsi"),
    ("Pepsi Cola 1,5lt.", "pepsi"),
    ("MELISSA Σπαγγέτι Χωρίς γλουτένη 400g", "melissa"),
    ("Melissa Σπαγγέτι Χωρίς Γλουτένη 400gr", "melissa"),
    ("PAMPERS Active Baby Pants Πάνες Βρακάκι Νο6 13-19kg 42τεμ", "pampers"),
    ("ΙΟΝ Derby Σοκολάτα Classic 3x38g +1 Δώρο", "ion"),
    ("LURPAK Βούτυρο Ελαφρώς Αλατισμένο 200g", "lurpak"),
    ("HEINZ Κέτσαπ Βιολογική 580g", "heinz"),
    ("RIO MARE Τόνος σε Ελαιόλαδο 3x80g", "rio-mare"),
    ("Rio Mare Τόνος Σε Ελαιόλαδο 3x80gr", "rio-mare"),
    ("Soflan Bivalent Υγρό Απορρυπαντικό Πλυντηρίου Ρούχων Classic 24mez. 960ml.", "soflan"),
    ("AJAX Καθαριστικό Πατώματος 1lt", "ajax"),
    ("PANTENE Hydration Recharge Κρέμα Conditioner 230ml", "pantene"),
    ("Nivea Sun Αντηλιακό Γαλάκτωμα SPF20 200ml", "nivea"),

    # Greek-script brand names.
    ("ΓΙΩΤΗΣ Πουτίγκα 70g", "yotis"),
    ("ΝΟΥΝΟΥ Family Πλήρες 1lt", "nounou"),
    ("Δωδώνη Φέτα 400g", "dodoni"),
    ("Μυθος Beer 500ml", "mythos"),
]

# Private-label products must NOT canonicalise — return None.
PRIVATE_LABEL_CASES: list[str] = [
    "My Gusto Πάριζα & Τυρί Gouda 280gr",
    "My Gusto Γαλοπούλα Βραστή & Τυρί Edam 280gr",
    "Μασούτης Φέτα Light 200gr",  # chain own-brand
]

# Look-alikes / negatives: must NOT mis-detect a brand.
NEGATIVE_CASES: list[str] = [
    "Σάλτσα Siciliana 400g",                     # no brand prefix at all
    "Δημητριακά Ολικής Άλεσης με Αμύγδαλα 325g",  # AB own-brand
    "Μπάρες Δημητριακών Protein Cocoa 4x20g",     # AB own-brand
]


@pytest.mark.parametrize("name,expected", KNOWN_BRAND_CASES)
def test_known_brand_detected(name: str, expected: str) -> None:
    assert extract_manufacturer(name) == expected, name


@pytest.mark.parametrize("name", PRIVATE_LABEL_CASES)
def test_private_label_returns_none(name: str) -> None:
    assert extract_manufacturer(name) is None, name


@pytest.mark.parametrize("name", NEGATIVE_CASES)
def test_unknown_returns_none(name: str) -> None:
    assert extract_manufacturer(name) is None, name


def test_lactacyd_is_not_lacta() -> None:
    """Sub-brand collision — `LACTACYD` must not match the `lacta` alias."""
    name = "LACTACYD Fresh Λοσιόν Καθαρισμού Ευαίσθητης Περιοχής 200ml"
    assert extract_manufacturer(name) == "lactacyd"


def test_aroma_melissas_is_not_melissa() -> None:
    """`AROMA MELISSAS` is honey, not the pasta brand."""
    name = "AROMA MELISSAS Μέλι Πεύκου Άγρια Βότανα 900g"
    assert extract_manufacturer(name) == "aroma-melissas"


def test_empty_input() -> None:
    assert extract_manufacturer("") is None
    assert extract_manufacturer("   ") is None
