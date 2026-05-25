"""Rule-based pairwise matcher.

Given two :class:`ProductFeatures`, decide whether they represent the same
canonical SKU. The matcher is deterministic and explainable — the embedding
fallback (in :mod:`scraper.canonical.embedding_matcher`) is only invoked
when this matcher returns an *uncertain* confidence in [0.4, 0.95].

Contract (also used as the design-doc reference):

  * Brand mismatch → not the same product (confidence 1.0).
  * Size mismatch → not the same product (confidence 1.0).
  * Pack mismatch → not the same product (confidence 1.0).
  * Same brand+size+pack+variant_tokens → same product, score 0.95..1.0
    depending on variant Jaccard overlap.
  * Same brand+size+pack but variant_tokens disagree → ambiguous (0.6);
    caller may escalate to embedding fallback.
"""

from __future__ import annotations

from typing import NamedTuple

from .extractors import ProductFeatures


class Decision(NamedTuple):
    same: bool
    confidence: float
    reason: str
    method: str


def match_decision(a: ProductFeatures, b: ProductFeatures) -> Decision:
    """Compare two feature tuples and return a :class:`Decision`."""
    # Both must have a confidently extracted manufacturer — own-brand /
    # unknown products are never cross-merged.
    if a.manufacturer is None or b.manufacturer is None:
        return Decision(False, 1.0, "manufacturer unknown", "rule")

    if a.manufacturer != b.manufacturer:
        return Decision(False, 1.0, "different brand", "rule")

    if a.size != b.size:
        return Decision(False, 1.0, f"size {a.size} vs {b.size}", "rule")

    if a.pack != b.pack:
        return Decision(False, 1.0, f"pack {a.pack} vs {b.pack}", "rule")

    # Variant comparison — Jaccard on the token sets.
    union = a.variant_tokens | b.variant_tokens
    intersection = a.variant_tokens & b.variant_tokens
    if not union:
        # Both sides stripped down to nothing (e.g. "Coca-Cola 1.5lt"
        # with no descriptor). Treat as a confident match.
        return Decision(True, 1.0, "no variant tokens — base SKU", "rule")

    jaccard = len(intersection) / len(union)

    if jaccard >= 0.5:
        confidence = 0.90 + 0.10 * jaccard
        return Decision(True, confidence, f"variant jaccard={jaccard:.2f}", "rule")

    if jaccard >= 0.25:
        # Ambiguous zone — same brand/size/pack but variants only partly
        # overlap. Embedding fallback may help; return a mid confidence.
        return Decision(False, 0.6, f"variant jaccard={jaccard:.2f}", "rule")

    return Decision(False, 0.95, f"variant mismatch jaccard={jaccard:.2f}", "rule")
