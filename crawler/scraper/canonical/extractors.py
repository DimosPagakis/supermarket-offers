"""Phase-1 deterministic field extractors.

Pure-Python (stdlib + `unicodedata`). Designed so each extractor can be
unit-tested in isolation and so the output is *deterministic* across
runs — given the same product name we must always derive the same
`canonical_key`, otherwise the comparison schema goes incoherent.

Pipeline:
    name  ──► extract_manufacturer()  ──┐
          ──► canonical_size()          ├──► ProductFeatures
          ──► pack_count()              │
          ──► variant_tokens()          ┘

The `canonical_key` is the natural identifier joined from
`(manufacturer, variant-slug, size, pack)`. Same key = same canonical
product, guaranteed.

Design lessons embedded here (from the embedding spike, see CLAUDE.md):

  * Embeddings happily merge "Pampers Pants No7" and "Pampers Pants No8".
    Therefore size (incl. the diaper/pasta `No` designator) must be a
    block-level discriminator, *not* a fuzzy signal.

  * Sklavenitis uppercases brand names ("BARILLA"), Masoutis title-cases
    them ("Barilla"), My Market is mixed. We normalise all to lowercase
    ASCII-folded form *before* alias matching.

  * "Nirvana Παγωτό 313γρ./420ml." gives two sizes. Volume (ml) wins for
    liquids/ice cream tubs because that's the package the manufacturer
    sells; the gram weight on Nirvana labels is the net contents, not
    the SKU identity.
"""

from __future__ import annotations

import re
import unicodedata
from typing import NamedTuple

from .brands import all_aliases, private_label_aliases

# ---------------------------------------------------------------------------
# Normalisation primitives — mirror the backend StringNormalizer so the
# canonical key we compute matches what the backend would see on its end.
# ---------------------------------------------------------------------------

_NONSPACING_RE = re.compile(r"[̀-ͯ]")


def _strip_accents(s: str) -> str:
    """NFD decompose, drop combining marks, NFC recompose."""
    return unicodedata.normalize(
        "NFC", _NONSPACING_RE.sub("", unicodedata.normalize("NFD", s))
    )


def _fold_lower(s: str) -> str:
    """Lowercase + accent-strip + whitespace-collapse. Greek letters are
    preserved (we don't fold to Latin here — that's an explicit step
    elsewhere)."""
    return re.sub(r"\s+", " ", _strip_accents(s).lower()).strip()


# Greek → Latin look-alike folding. Matches the design doc's "aggressive
# match key" — most Greek lowercase letters have a Latin twin that visually
# resembles them, and chains mix the two (e.g. "Bιολογικό" with a Latin B).
_GREEK_TO_LATIN = str.maketrans({
    "α": "a", "β": "b", "γ": "g", "δ": "d", "ε": "e", "ζ": "z", "η": "h",
    "θ": "th", "ι": "i", "κ": "k", "λ": "l", "μ": "m", "ν": "n", "ξ": "x",
    "ο": "o", "π": "p", "ρ": "r", "σ": "s", "τ": "t", "υ": "y", "φ": "f",
    "χ": "x", "ψ": "ps", "ω": "o", "ς": "s",
})


def _fold_to_ascii(s: str) -> str:
    """Lowercase + accent strip + Greek→Latin look-alike fold."""
    return _fold_lower(s).translate(_GREEK_TO_LATIN)


# ---------------------------------------------------------------------------
# Manufacturer extractor
# ---------------------------------------------------------------------------

_BRAND_ALIASES = all_aliases()       # longest first
_PRIVATE_ALIASES = private_label_aliases()


def extract_manufacturer(name: str) -> str | None:
    """Return the manufacturer brand name normalised to its canonical key
    (e.g. ``"lacta"``, ``"nirvana"``, ``"coca-cola"``).

    Strategy:
        1. Match against `brands.BRANDS` (≈120 known national brands) by
           accent-stripped lowercase substring + leading-token check.
           Greedy: try longest alias first.
        2. If the name matches a private-label alias (e.g. ``"my gusto"``),
           return ``None`` — the caller MUST NOT canonicalise these
           cross-chain.
        3. Otherwise return ``None`` ("unknown / own-brand"). Caller skips
           these products from canonicalisation.

    The frequency-learning fallback described in the design doc is *not*
    enabled here — frequency-based brand inference is left for Phase 2 once
    we have ground-truth labelled clusters to validate against. Returning
    ``None`` is the safe default; the design doc explicitly says
    "fail closed".
    """
    if not name:
        return None
    folded = _fold_lower(name)

    # Private-label check first — wins over any accidental national-brand
    # alias substring match, since these names often start with the store
    # tag (e.g. "My Gusto", "AB ").
    for alias, _ in _PRIVATE_ALIASES:
        if _alias_matches(folded, alias):
            return None

    for alias, canonical in _BRAND_ALIASES:
        if _alias_matches(folded, alias):
            return canonical
    return None


def _alias_matches(folded_name: str, alias: str) -> bool:
    """True iff `alias` appears as a leading token of `folded_name`,
    optionally preceded by stray punctuation. Examples:
        folded_name="lacta nuts σοκολατα γαλακτος ..."  alias="lacta" -> True
        folded_name="lactacyd fresh λοσιον ..."          alias="lacta" -> False
        folded_name="rio mare τονος ..."                 alias="rio mare" -> True
        folded_name="kri-kri γιαουρτι ..."               alias="kri-kri" -> True
    """
    if not alias:
        return False
    # Use re.escape + word-boundary semantics by hand: we want the alias
    # to be followed by whitespace, end of string, or one of a small set
    # of punctuation chars.
    pattern = (
        r"(?:^|[\s\-/.,(\[])"          # at start or after a separator
        + re.escape(alias)
        + r"(?=$|[\s\-/.,)\]])"         # ends at end / separator
    )
    m = re.search(pattern, folded_name)
    if not m:
        return False
    # Only count it as a brand match if the alias appears at the very
    # *start* of the title — Greek listings lead with the manufacturer
    # in >99% of cases. Allowing matches deeper in the title cascades
    # into false positives like "O.B. Pro Comfort" matching the
    # `comfort` softener brand. Allow at most one preceding token to
    # cover names like "Mr Grand" preceded by a leftover article.
    head = folded_name[: m.start() + 1].strip()
    leading_words = len(head.split())
    return leading_words <= 1


# ---------------------------------------------------------------------------
# Size extractor
# ---------------------------------------------------------------------------

# Order matters in the unit alternation — longer literals first so "lt"
# doesn't get gobbled by "l".
_UNIT_MAP: list[tuple[str, str]] = [
    # canonical 'g' (grams)
    ("γραμμαρια", "g"),
    ("γραμμάρια", "g"),
    ("γρ.", "g"),
    ("γρ", "g"),
    ("gr.", "g"),
    ("gr", "g"),
    ("g.", "g"),
    ("g", "g"),
    # canonical 'kg'
    ("κιλά", "kg"),
    ("κιλα", "kg"),
    ("κιλό", "kg"),
    ("κιλο", "kg"),
    ("κιλ.", "kg"),
    ("κιλ", "kg"),
    ("kg.", "kg"),
    ("kg", "kg"),
    # canonical 'ml'
    ("ml.", "ml"),
    ("ml", "ml"),
    ("μλ", "ml"),
    # canonical 'l' (litres)
    ("λίτρα", "l"),
    ("λιτρα", "l"),
    ("λτ.", "l"),
    ("λτ", "l"),
    ("lt.", "l"),
    ("lt", "l"),
    ("l.", "l"),
    ("l", "l"),
    # canonical 'τεμ' (pieces)
    ("τεμάχια", "τεμ"),
    ("τεμαχια", "τεμ"),
    ("τεμάχιο", "τεμ"),
    ("τεμαχιο", "τεμ"),
    ("τεμ.", "τεμ"),
    ("τεμ", "τεμ"),
    ("τμχ.", "τεμ"),
    ("τμχ", "τεμ"),
    ("pcs.", "τεμ"),
    ("pcs", "τεμ"),
    ("ρολλά", "τεμ"),
    ("ρολλα", "τεμ"),
    ("ρολά", "τεμ"),
    ("ρολα", "τεμ"),
    ("φύλλα", "τεμ"),
    ("φυλλα", "τεμ"),
    ("μερίδες", "τεμ"),
    ("μεριδες", "τεμ"),
    ("μεζούρες", "τεμ"),
    ("μεζουρες", "τεμ"),
]

# After accent-stripping/lowercase, the same map collapses further.
_UNIT_MAP_FOLDED: list[tuple[str, str]] = sorted(
    {(_fold_lower(u), c) for u, c in _UNIT_MAP},
    key=lambda p: -len(p[0]),
)

# Volume-canonical units win over weight when both appear (e.g. ice cream
# "313γρ./420ml" — the 420 ml tub is the SKU).
_VOLUME_UNITS = {"ml", "l"}
_WEIGHT_UNITS = {"g", "kg"}

# Designator units (e.g. diaper "No7") carry no decimal commas and behave
# like sizes for blocking purposes — but they're not a quantity.
_DESIGNATOR_UNITS = {"no"}


# A size match is: optional 'No'/'Νο' prefix, number with Greek decimal
# comma allowed, optional whitespace, unit token. We deliberately also
# match the 'No <digit>' diaper designator and 'Νο<digit>' Greek variant.

# Number with optional decimal.  Greek uses comma (`1,5`), Latin sometimes
# dot (`1.5`).
_NUM_RE = r"(\d+(?:[.,]\d+)?)"


def _build_size_regex() -> re.Pattern:
    # Build a single alternation of unit aliases as one capture group.
    # The grammar covers three shapes:
    #   1.  "<no|νο> <int>"                    → designator size (No7, Νο6)
    #   2.  "<num> <unit>"                     → ordinary size (400g, 1,5lt)
    #   3.  "<num> <no|νο>"                    → designator size (5No)
    # We use one alternation so finditer returns matches in lexical order.
    unit_alt = "|".join(re.escape(u) for u, _ in _UNIT_MAP_FOLDED)
    designator_prefix = (
        r"(?<![a-zα-ω0-9])(no|νο)\s*(\d+)(?![a-zα-ω0-9.,])"
    )
    num_with_unit = (
        _NUM_RE
        + r"\s*"
        + f"(?:({unit_alt})(?![a-zα-ω])|(?<=\\d)(no|νο)(?![a-zα-ω0-9]))"
    )
    pat = f"(?:{designator_prefix})|(?:{num_with_unit})"
    return re.compile(pat, flags=re.IGNORECASE)


_SIZE_RE = _build_size_regex()


def _to_float(num_str: str) -> float:
    """Parse '1,5' or '1.5' → 1.5."""
    return float(num_str.replace(",", "."))


def _normalise_unit(raw: str) -> str:
    raw = raw.lower()
    for alias, canonical in _UNIT_MAP_FOLDED:
        if alias == raw:
            return canonical
    return raw


def canonical_size(name: str) -> tuple[float, str] | None:
    """Extract ``(value, unit_canonical)`` from a product name.

    Returns ``None`` if no size detected. Examples:

        "Lacta Γκοφρέτα 28,5γρ"             → (28.5, 'g')
        "Coca-Cola 1,5lt"                    → (1.5, 'l')
        "Nirvana Παγωτό 313g (420ml)"        → (420.0, 'ml')
        "Pampers Pants No7 38τεμ"            → (7.0, 'no')   ← designator wins
        "Pampers Pants Νο6 13-19kg 42τεμ"    → (6.0, 'no')
        "MELISSA Σπαγγέτι Χωρίς γλουτένη 400g" → (400.0, 'g')

    Resolution rules when multiple sizes appear:
      1. A ``No``/``Νο`` designator (diaper/pasta size) wins outright — it's
         the SKU identifier on those product families.
      2. Volume (ml/l) beats weight (g/kg) when both appear — covers the
         Nirvana ice-cream "313γρ./420ml" pattern across all chains.
      3. Otherwise pick the LAST occurrence (sizes trail brand and variant
         in Greek listings).
    """
    if not name:
        return None
    folded = _fold_lower(name)

    # Group layout (see _build_size_regex):
    #   1: designator prefix word (no|νο)        + 2: designator number
    #   3: numeric value          + 4: unit alias + 5: suffix-no
    matches: list[tuple[float, str, int]] = []   # (value, unit, position)
    for m in _SIZE_RE.finditer(folded):
        if m.group(1):              # designator prefix branch
            value = _to_float(m.group(2))
            if value.is_integer():
                matches.append((value, "no", m.start()))
            continue
        if m.group(5):              # designator suffix branch (5No)
            value = _to_float(m.group(3))
            if value.is_integer():
                matches.append((value, "no", m.start()))
            continue
        if m.group(4):              # unit branch
            value = _to_float(m.group(3))
            unit = _normalise_unit(m.group(4))
            matches.append((value, unit, m.start()))

    if not matches:
        return None

    # 1. Designator wins.
    designators = [m for m in matches if m[1] in _DESIGNATOR_UNITS]
    if designators:
        # Filter out designators that look like a price label "νο 7 X 23.5gr"
        # — these will always be followed by a more concrete weight/volume
        # match in the same string, but we still prefer the designator since
        # for those product families (pasta, diapers) the No IS the SKU.
        v, u, _ = designators[-1]
        return (v, u)

    # 2. Volume wins.
    vol = [m for m in matches if m[1] in _VOLUME_UNITS]
    if vol:
        v, u, _ = vol[-1]
        # Normalise to ml when sub-litre values are reported as 'l'.
        # (Some chains write '0,5lt' but we keep it as l to retain the
        # author's intent.)
        return (v, u)

    # 3. Last occurrence wins.
    v, u, _ = matches[-1]
    return (v, u)


# ---------------------------------------------------------------------------
# Pack count extractor
# ---------------------------------------------------------------------------

# Matches '2x1lt', '3x28,5g', '6 X 23.5gr', '6×500ml'. The number BEFORE the
# 'x' is the pack count.
_PACK_RE = re.compile(
    r"(?<![a-z0-9])(\d{1,2})\s*[x×Χχ]\s*(?=\d)",
    flags=re.IGNORECASE,
)

# Diaper sizes look the same — "13-19kg" — but the 'kg' makes the right
# half non-numeric, so the lookahead above prevents a match. Good.

# Designators we explicitly exclude from being interpreted as packs:
#   'No7' (already a size), 'SPF20', 'φεταρόλο 2x'.

# Special promo phrases: '+1 Δώρο' is the +1 free bottle promo. Counts as +1.
_PLUS_FREE_RE = re.compile(
    r"\+\s*(\d{1,2})\s*(?:δωρο|δώρο|free|gift)",
    flags=re.IGNORECASE,
)


def pack_count(name: str) -> int:
    """Extract the multi-pack count from patterns like ``2x1lt`` or
    ``3x28g``. Returns 1 (singleton) when no multi-pack pattern is found.

    The ``+N Δώρο`` promo suffix ("5×330ml +1 Δώρο") is folded into the
    base pack count when present — so the Sklavenitis "5x330ml +1 Δώρο"
    and the My Market "6x330ml" come out as the same pack of 6.

    Examples::

        "Coca-Cola 2x1lt"                    → 2
        "Lacta 3x28,5γρ"                     → 3
        "Nirvana Παγωτό 420ml"               → 1
        "COCA-COLA Original Taste 5x330ml +1 Δώρο" → 6
    """
    if not name:
        return 1
    folded = _fold_lower(name)
    base = 1
    pack_match = _PACK_RE.search(folded)
    if pack_match:
        try:
            n = int(pack_match.group(1))
            if 1 <= n <= 48:
                base = n
        except ValueError:
            pass

    plus_match = _PLUS_FREE_RE.search(folded)
    if plus_match:
        try:
            extra = int(plus_match.group(1))
            if 1 <= extra <= 12:
                base += extra
        except ValueError:
            pass

    return base


# ---------------------------------------------------------------------------
# Variant tokens
# ---------------------------------------------------------------------------

# Tokens we deliberately drop because they're packaging chatter, not
# product-identity. Folded to ASCII for matching.
_STOPWORDS: frozenset[str] = frozenset({
    # english
    "the", "of", "and", "with", "for", "in", "on", "from", "to", "at",
    "pack", "value", "new",
    # greek (ASCII-folded forms) — "to" is shared with the English set,
    # so it's listed once above.
    "kai", "me", "se", "sto", "sthn", "stoys", "stis", "toy", "ths", "ton",
    "twn", "h", "o", "ta", "oi", "oti", "ena", "mia",
    # generic descriptor noise
    "tem", "temaxio", "temaxia", "tmx",
    "fyllo", "fylla", "rolla", "rola", "merides",
})

_TOKEN_SPLIT_RE = re.compile(r"[^a-zα-ω0-9]+", flags=re.IGNORECASE)


def _strip_brand(folded: str, brand_canonical: str | None) -> str:
    """Remove brand alias occurrences from the folded name."""
    if not brand_canonical:
        return folded
    out = folded
    for alias, canonical in _BRAND_ALIASES:
        if canonical != brand_canonical:
            continue
        out = re.sub(
            r"(?:^|(?<=[\s\-/.,(\[]))" + re.escape(alias) + r"(?=$|[\s\-/.,)\]])",
            " ",
            out,
        )
    return out


def _strip_size_and_pack(folded: str) -> str:
    """Remove size tokens (incl. designators) and pack-count tokens."""
    # Order matters: kill the pack pattern *before* the size regex eats
    # the digits on its right-hand side ("2x1lt" → kill "2x" + "1lt").
    out = _PACK_RE.sub(" ", folded)
    # Drop residual "Nx" tokens (e.g. "5x" left behind when a size also
    # appeared) so they don't leak into the variant slug.
    out = re.sub(r"\b\d{1,2}\s*[x×]\b", " ", out)
    out = _SIZE_RE.sub(" ", out)
    out = _PLUS_FREE_RE.sub(" ", out)
    # Remaining standalone numbers — almost certainly stray size / promo
    # residue. Drop to avoid spurious variant differences.
    out = re.sub(r"\b\d+(?:[.,]\d+)?\b", " ", out)
    # Drop any residual lone 'x' that survived the pack stripping.
    out = re.sub(r"\bx\b", " ", out)
    return out


def variant_tokens(
    name: str,
    manufacturer: str | None,
    size: tuple[float, str] | None,
) -> frozenset[str]:
    """Tokens left after stripping brand + size + pack + stopwords.

    Tokens are Greek-accent-folded to ASCII so "Φουντουκιού" and
    "ΦΟΥΝΤΟΥΚΙΟΥ" both reduce to ``foyntoykioy``. Punctuation is dropped.

    ``size`` is accepted but currently used only to confirm the size
    sub-string is gone after stripping — we don't subtract it twice.
    """
    if not name:
        return frozenset()

    folded = _fold_lower(name)
    folded = _strip_brand(folded, manufacturer)
    folded = _strip_size_and_pack(folded)

    # Greek→Latin fold so tokens are comparable across script choices.
    ascii_folded = folded.translate(_GREEK_TO_LATIN)
    raw_tokens = (t for t in _TOKEN_SPLIT_RE.split(ascii_folded) if t)
    tokens = {
        t for t in raw_tokens
        if len(t) >= 2 and t not in _STOPWORDS and not t.isdigit()
    }
    return frozenset(tokens)


# ---------------------------------------------------------------------------
# Canonical key
# ---------------------------------------------------------------------------

_SLUG_PUNCT_RE = re.compile(r"[^a-z0-9]+")


def _slug(tokens: frozenset[str], max_tokens: int = 4) -> str:
    """Order tokens deterministically, take the first N, hyphen-join."""
    ordered = sorted(tokens)
    head = ordered[:max_tokens]
    return _SLUG_PUNCT_RE.sub("-", "-".join(head)).strip("-") or "x"


def canonical_key(
    manufacturer: str,
    size: tuple[float, str] | None,
    pack: int,
    variant: frozenset[str],
) -> str:
    """Build a deterministic identifier of the form
    ``manufacturer:variant-slug:size:pack``.

    Examples::

        canonical_key("lacta", (31.0, "g"), 1, frozenset({"gofreta","foyntoyki"}))
            → "lacta:foyntoyki-gofreta:31g:1"

        canonical_key("coca-cola", (1.5, "l"), 2, frozenset())
            → "coca-cola:x:1.5l:2"
    """
    size_part = _format_size(size)
    variant_part = _slug(variant)
    return f"{manufacturer}:{variant_part}:{size_part}:{pack}"


def _format_size(size: tuple[float, str] | None) -> str:
    if size is None:
        return "nosize"
    v, u = size
    if float(v).is_integer():
        return f"{int(v)}{u}"
    # avoid trailing zeros — 1.50 → 1.5
    return f"{v:g}{u}"


# ---------------------------------------------------------------------------
# ProductFeatures — convenience container used by matcher and batch script
# ---------------------------------------------------------------------------


class ProductFeatures(NamedTuple):
    product_id: int
    brand_slug: str
    name: str
    manufacturer: str | None
    size: tuple[float, str] | None
    pack: int
    variant_tokens: frozenset[str]
    canonical_key: str | None
    category: str | None = None


def extract_features(
    product_id: int,
    brand_slug: str,
    name: str,
    category: str | None = None,
) -> ProductFeatures:
    """Run all extractors and produce a ProductFeatures NamedTuple."""
    manufacturer = extract_manufacturer(name)
    size = canonical_size(name)
    pack = pack_count(name)
    variant = variant_tokens(name, manufacturer, size)
    key = (
        canonical_key(manufacturer, size, pack, variant)
        if manufacturer is not None
        else None
    )
    return ProductFeatures(
        product_id=product_id,
        brand_slug=brand_slug,
        name=name,
        manufacturer=manufacturer,
        size=size,
        pack=pack,
        variant_tokens=variant,
        canonical_key=key,
        category=category,
    )
