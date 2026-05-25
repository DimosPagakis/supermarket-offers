"""Phase 1 product canonicalisation: field extractors, rule-based matcher,
optional embedding fallback, and a batch driver.

This is a pure-algorithm package — no Scrapy imports, no spider runtime
dependencies. The batch script under `crawler/scripts/canonicalise.py`
talks to the backend public API to pull products and POST groupings.
"""

from .extractors import (
    ProductFeatures,
    canonical_key,
    canonical_size,
    extract_features,
    extract_manufacturer,
    pack_count,
    variant_tokens,
)
from .matcher import Decision, match_decision

__all__ = [
    "Decision",
    "ProductFeatures",
    "canonical_key",
    "canonical_size",
    "extract_features",
    "extract_manufacturer",
    "match_decision",
    "pack_count",
    "variant_tokens",
]
