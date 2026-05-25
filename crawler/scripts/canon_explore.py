"""
canon_explore.py — Read-only helper used while designing the product
canonicalisation system (see `docs/canonicalisation-design.md`).

Pulls offers from the local public API on :8001, groups them by an
attempted match key, and prints brand-spanning cluster candidates so we
can eyeball where exact / fuzzy / embedding matching would land.

This is NOT production code. It is a scratch tool. Re-run it after a
fresh crawl to refresh the example set.

Usage:
    python crawler/scripts/canon_explore.py                  # cluster summary
    python crawler/scripts/canon_explore.py search coca      # raw search
    python crawler/scripts/canon_explore.py tier easy        # tiered examples

Requires only the stdlib (urllib + json). No virtualenv needed.
"""

from __future__ import annotations

import json
import re
import sys
import unicodedata
import urllib.parse
import urllib.request
from collections import defaultdict
from typing import Iterable

API = "http://127.0.0.1:8001/api/public/v1"


# ---------- HTTP ----------------------------------------------------------

def fetch(path: str, **params) -> dict:
    qs = urllib.parse.urlencode(params)
    url = f"{API}/{path}" + (f"?{qs}" if qs else "")
    with urllib.request.urlopen(url, timeout=15) as r:
        return json.loads(r.read().decode("utf-8"))


def iter_offers(**filters) -> Iterable[dict]:
    """Yield every offer matching filters, paging through results."""
    page = 1
    while True:
        body = fetch("offers", per_page=100, page=page, **filters)
        for row in body.get("data", []):
            yield row
        meta = body.get("meta", {})
        if page >= (meta.get("last_page") or 1):
            return
        page += 1


# ---------- Normalisation (mirrors backend StringNormalizer) --------------

_NONSPACING = re.compile(r"[̀-ͯ]")


def normalize(name: str) -> str:
    s = unicodedata.normalize("NFD", name.lower())
    s = _NONSPACING.sub("", s)
    s = unicodedata.normalize("NFC", s)
    return re.sub(r"\s+", " ", s).strip()


# Extended normalisation: also fold size hints, punctuation, latin/greek
# look-alikes. This is the candidate Phase-1 "match key".
_SIZE_NUM = re.compile(r"(\d+)[\.,](\d+)")
_SPACE_BEFORE_UNIT = re.compile(
    r"(\d)\s*(ml|l|lt|λτ|λιτ|gr|g|γρ|κιλ|kg|τεμ|pcs|pack|τμχ)\b"
)
_PUNCT = re.compile(r"[\.,/()\[\]+*'\"`!?]")
_LATIN_GREEK_LOOKALIKES = {
    # Greek -> latin lower
    "α": "a", "β": "b", "ε": "e", "ζ": "z", "η": "h", "ι": "i", "κ": "k",
    "μ": "m", "ν": "n", "ο": "o", "π": "p", "ρ": "r", "τ": "t", "υ": "y",
    "χ": "x",
}


def match_key(name: str, *, fold_letters: bool = False) -> str:
    """Aggressive normalisation used as a blocking key candidate."""
    s = normalize(name)
    s = _SIZE_NUM.sub(r"\1.\2", s)            # "1,5" -> "1.5"
    s = _SPACE_BEFORE_UNIT.sub(r"\1\2", s)    # "330 ml" -> "330ml"
    s = s.replace("lt", "l").replace("λτ", "l").replace("λιτ", "l")
    s = s.replace("γρ", "g").replace("gr", "g")
    s = _PUNCT.sub(" ", s)
    if fold_letters:
        s = "".join(_LATIN_GREEK_LOOKALIKES.get(c, c) for c in s)
    return re.sub(r"\s+", " ", s).strip()


# ---------- Reports -------------------------------------------------------

def cluster_report(min_brands: int = 2) -> None:
    """Group all offers by aggressive match_key and print clusters that
    span >= min_brands distinct brands.
    """
    bucket: dict[str, list[dict]] = defaultdict(list)
    for o in iter_offers():
        key = match_key(o["product"]["name"], fold_letters=True)
        bucket[key].append(o)

    multi = [
        (k, rows) for k, rows in bucket.items()
        if len({r["brand"]["slug"] for r in rows}) >= min_brands
    ]
    multi.sort(key=lambda kr: -len({r["brand"]["slug"] for r in kr[1]}))
    print(f"# {len(multi)} cluster(s) with >= {min_brands} brands")
    for key, rows in multi[:40]:
        brands = sorted({r["brand"]["slug"] for r in rows})
        print(f"\n## key='{key}'  brands={brands}")
        for r in rows:
            print(
                f"  {r['brand']['slug']:12} p={r['product']['id']:>6} "
                f"€{r['price']:<5}  {r['product']['name']}"
            )


def search(term: str) -> None:
    body = fetch("offers", q=term, per_page=30)
    for o in body.get("data", []):
        p, b = o["product"], o["brand"]
        print(
            f"{b['slug']:12} p={p['id']:>6}  €{o['price']:<5}  "
            f"unit={p.get('unit') or '-':<12}  {p['name']}"
        )


_TIER_QUERIES = {
    "easy":   ["nirvana", "barilla", "lacta", "mythos"],
    "medium": ["coca", "nescafe", "heineken"],
    "hard":   ["feta", "ηπειρος", "gouda"],
    "own":    ["my gusto", "ab "],
    "typo":   ["pop", "βιολογικ", "xtra"],
    "flavour": ["apaki", "nirvana"],
}


def tier_examples(tier: str) -> None:
    for q in _TIER_QUERIES.get(tier, []):
        print(f"\n=== q={q!r} ===")
        try:
            search(q)
        except Exception as e:
            print(f"  (failed: {e})")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        cluster_report()
    elif args[0] == "search" and len(args) >= 2:
        search(" ".join(args[1:]))
    elif args[0] == "tier" and len(args) >= 2:
        tier_examples(args[1])
    else:
        print(__doc__)
        sys.exit(1)
