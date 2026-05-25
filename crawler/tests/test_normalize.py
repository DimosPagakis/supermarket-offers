"""Unit tests for scraper.normalize."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from scraper.normalize import (
    clean_text,
    parse_date,
    parse_date_range,
    parse_discount_pct,
    parse_price,
)


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("4,99 €", Decimal("4.99")),
        ("4.99€", Decimal("4.99")),
        ("€4,99", Decimal("4.99")),
        ("  4,99  ", Decimal("4.99")),
        ("4,9", Decimal("4.9")),
        ("12", Decimal("12")),
        ("1.234,56", Decimal("1234.56")),
        ("1,234.56", Decimal("1234.56")),
        ("Από 4,99€", Decimal("4.99")),
    ],
)
def test_parse_price_valid(raw: str, expected: Decimal) -> None:
    assert parse_price(raw) == expected


@pytest.mark.parametrize("raw", [None, "", "   ", "no digits here"])
def test_parse_price_invalid(raw: str | None) -> None:
    assert parse_price(raw) is None


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("-23%", 23),
        ("23 %", 23),
        ("έκπτωση 23%", 23),
        ("Save 50%", 50),
        ("0%", 0),
    ],
)
def test_parse_discount_pct_valid(raw: str, expected: int) -> None:
    assert parse_discount_pct(raw) == expected


@pytest.mark.parametrize("raw", [None, "", "no percent", "150%"])
def test_parse_discount_pct_invalid(raw: str | None) -> None:
    assert parse_discount_pct(raw) is None


def test_parse_date_numeric_full() -> None:
    assert parse_date("28/05/2026") == date(2026, 5, 28)
    assert parse_date("28-05-26") == date(2026, 5, 28)
    assert parse_date("28.05.2026") == date(2026, 5, 28)


def test_parse_date_numeric_short_uses_default_year() -> None:
    assert parse_date("28.05", default_year=2026) == date(2026, 5, 28)


def test_parse_date_greek_long() -> None:
    assert parse_date("28 Μαΐου 2026") == date(2026, 5, 28)
    assert parse_date("3 Ιουνίου 2026") == date(2026, 6, 3)


def test_parse_date_invalid() -> None:
    assert parse_date(None) is None
    assert parse_date("") is None
    assert parse_date("blah") is None
    # Invalid day/month combo:
    assert parse_date("32/13/2026") is None


def test_parse_date_range_two_dates() -> None:
    frm, to = parse_date_range("Από 28.05 έως 03.06", default_year=2026)
    assert frm == date(2026, 5, 28)
    assert to == date(2026, 6, 3)


def test_parse_date_range_dash() -> None:
    frm, to = parse_date_range("28/05/2026 - 03/06/2026")
    assert frm == date(2026, 5, 28)
    assert to == date(2026, 6, 3)


def test_parse_date_range_single() -> None:
    frm, to = parse_date_range("Από 28.05", default_year=2026)
    assert frm == date(2026, 5, 28)
    assert to is None


def test_parse_date_range_none() -> None:
    assert parse_date_range(None) == (None, None)
    assert parse_date_range("") == (None, None)
    assert parse_date_range("no dates here") == (None, None)


def test_clean_text() -> None:
    assert clean_text("  hello   world  ") == "hello world"
    assert clean_text("hello\n\tworld") == "hello world"
    assert clean_text(None) is None
    assert clean_text("   ") is None
