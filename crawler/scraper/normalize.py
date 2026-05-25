"""String -> typed value helpers for noisy supermarket flyer data.

Kept dependency-free and side-effect-free so they're easy to unit test.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

# Matches a Greek-style price: "4,99 €", "4.99€", "€4,99", "1.234,56", etc.
_PRICE_RE = re.compile(
    # Matches a number with optional thousands separators (`.`, `,`, space)
    # and a 1-2 digit fractional part.
    #   1.234,56   1,234.56   1 234,56   4,99   12
    r"(?P<num>\d{1,3}(?:[.,\s]\d{3})+(?:[.,]\d{1,2})?|\d+(?:[.,]\d{1,2})?)"
)

# A loose date matcher for things like "28.05", "28/05/2026", "28-05-26".
_DATE_RE = re.compile(
    r"(?P<d>\d{1,2})[./\-](?P<m>\d{1,2})(?:[./\-](?P<y>\d{2,4}))?"
)

# Greek months in nominative + genitive (flyers use both).
_GREEK_MONTHS = {
    "ιανουαριου": 1, "ιανουάριος": 1, "ιανουαρίου": 1,
    "φεβρουαριου": 2, "φεβρουάριος": 2, "φεβρουαρίου": 2,
    "μαρτιου": 3, "μάρτιος": 3, "μαρτίου": 3,
    "απριλιου": 4, "απρίλιος": 4, "απριλίου": 4,
    "μαιου": 5, "μάιος": 5, "μαΐου": 5,
    "ιουνιου": 6, "ιούνιος": 6, "ιουνίου": 6,
    "ιουλιου": 7, "ιούλιος": 7, "ιουλίου": 7,
    "αυγουστου": 8, "αύγουστος": 8, "αυγούστου": 8,
    "σεπτεμβριου": 9, "σεπτέμβριος": 9, "σεπτεμβρίου": 9,
    "οκτωβριου": 10, "οκτώβριος": 10, "οκτωβρίου": 10,
    "νοεμβριου": 11, "νοέμβριος": 11, "νοεμβρίου": 11,
    "δεκεμβριου": 12, "δεκέμβριος": 12, "δεκεμβρίου": 12,
}


def parse_price(raw: str | None) -> Decimal | None:
    """Parse a flyer price string into a Decimal.

    Handles:
        "4,99 €" -> Decimal("4.99")
        "4.99€"  -> Decimal("4.99")
        "€4,99"  -> Decimal("4.99")
        "1.234,56" -> Decimal("1234.56")
        None / unparsable -> None
    """
    if raw is None:
        return None
    text = raw.strip()
    if not text:
        return None

    match = _PRICE_RE.search(text)
    if not match:
        return None

    num = match.group("num")

    # If both `.` and `,` appear, the LAST separator is the decimal one
    # (covers both "1,234.56" and "1.234,56").
    if "." in num and "," in num:
        if num.rfind(",") > num.rfind("."):
            num = num.replace(".", "").replace(",", ".")
        else:
            num = num.replace(",", "")
    elif "," in num:
        # Comma alone -> decimal separator (Greek convention).
        num = num.replace(",", ".")
    # If only "." appears, leave as-is (already a valid decimal).

    num = num.replace(" ", "")

    try:
        return Decimal(num)
    except InvalidOperation:
        return None


def parse_discount_pct(raw: str | None) -> int | None:
    """Parse a discount percentage like '-23%', '23 %', 'έκπτωση 23%'."""
    if raw is None:
        return None
    match = re.search(r"(\d{1,3})\s*%", raw)
    if not match:
        return None
    pct = int(match.group(1))
    if 0 <= pct <= 100:
        return pct
    return None


def parse_date(raw: str | None, *, default_year: int | None = None) -> date | None:
    """Parse common Greek flyer date strings into a `date`.

    Supports numeric forms ("28.05", "28/05/2026", "28-05-26") and
    long Greek forms ("28 Μαΐου 2026").
    """
    if raw is None:
        return None
    text = raw.strip().lower()
    if not text:
        return None

    # Try long Greek form first: "28 Μαΐου 2026" / "28 μαΐου"
    long_match = re.search(
        r"(?P<d>\d{1,2})\s+(?P<m>[α-ωίόύήέώϊϋΐΰ]+)(?:\s+(?P<y>\d{4}))?",
        text,
    )
    if long_match:
        month_word = long_match.group("m")
        if month_word in _GREEK_MONTHS:
            day = int(long_match.group("d"))
            month = _GREEK_MONTHS[month_word]
            year_str = long_match.group("y")
            year = int(year_str) if year_str else (default_year or datetime.now().year)
            try:
                return date(year, month, day)
            except ValueError:
                return None

    # Fallback: numeric.
    match = _DATE_RE.search(text)
    if not match:
        return None
    day = int(match.group("d"))
    month = int(match.group("m"))
    year_str = match.group("y")
    if year_str:
        year = int(year_str)
        if year < 100:
            year += 2000
    else:
        year = default_year or datetime.now().year
    try:
        return date(year, month, day)
    except ValueError:
        return None


def parse_date_range(
    raw: str | None, *, default_year: int | None = None
) -> tuple[date | None, date | None]:
    """Parse a flyer validity range like 'Από 28.05 έως 03.06' or '28/05 - 03/06'.

    Returns (valid_from, valid_to). Either or both may be None.
    """
    if raw is None:
        return (None, None)
    text = raw.strip()
    if not text:
        return (None, None)

    matches = list(_DATE_RE.finditer(text))
    if not matches:
        return (None, None)

    if len(matches) == 1:
        first = parse_date(matches[0].group(0), default_year=default_year)
        return (first, None)

    first = parse_date(matches[0].group(0), default_year=default_year)
    second = parse_date(matches[-1].group(0), default_year=default_year)
    return (first, second)


def clean_text(raw: str | None) -> str | None:
    """Collapse whitespace and strip; return None for empty input."""
    if raw is None:
        return None
    cleaned = re.sub(r"\s+", " ", raw).strip()
    return cleaned or None


def to_decimal(value: Any) -> Decimal | None:
    """Coerce a JSON-number / numeric-string into a Decimal.

    Round-trips through ``str()`` so floats don't drag their binary
    imprecision into the Decimal. Returns ``None`` for anything that
    won't parse (including ``None`` itself).

    Used across the per-brand parsers for fields the storefront already
    serves as JSON numbers — see ``parse_price`` for the noisier
    free-text variant that handles currency symbols and Greek thousands
    separators.
    """
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
