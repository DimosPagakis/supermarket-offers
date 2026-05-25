"""Group :class:`ProductFeatures` by canonical_key and shape them into the
payload the backend's ``/api/v1/canonical-products/bulk-upsert`` endpoint
expects.

Lives in :mod:`scraper.canonical` (alongside the extractors) instead of in
the script so it can be tested in isolation.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from .extractors import ProductFeatures
from .matcher import match_decision


def build_groups(
    features: Iterable[ProductFeatures],
) -> dict[str, list[ProductFeatures]]:
    """Bucket every feature with a non-None canonical_key by that key."""
    buckets: dict[str, list[ProductFeatures]] = defaultdict(list)
    for f in features:
        if f.canonical_key is None:
            continue
        buckets[f.canonical_key].append(f)
    return buckets


def group_to_payload(key: str, members: list[ProductFeatures]) -> dict:
    """Convert one (canonical_key, members) bucket into the
    ``canonical-products/bulk-upsert`` payload entry.

    The display name is chosen as the longest member name (most
    descriptive across chains). The variant_descriptor is the title-cased
    join of the canonical variant tokens (deterministic order).
    """
    assert members, "group_to_payload called with no members"

    # Pick the longest name as the display anchor — it's usually the one
    # with the most descriptors (Sklavenitis tends to win here).
    display = max(members, key=lambda f: len(f.name))

    # Confidence per member: 1.0 within a single canonical_key group (they
    # all literally matched the deterministic key). We still run the rule
    # matcher pairwise vs the anchor to surface any oddities — if it
    # disagrees we drop confidence to 0.85 so a backend reviewer notices.
    anchor = members[0]
    member_payload: list[dict] = []
    for m in members:
        decision = match_decision(anchor, m)
        confidence = 1.0 if decision.same else 0.85
        member_payload.append(
            {
                "product_id": m.product_id,
                "confidence": round(confidence, 3),
                "match_method": "rule",
            }
        )

    # Top-K tokens — same K we slug for canonical_key so the descriptor
    # stays a stable summary, not a kitchen-sink of every adjective.
    variant_descriptor = (
        " ".join(t.title() for t in sorted(anchor.variant_tokens)[:4])
        if anchor.variant_tokens
        else None
    )

    return {
        "canonical_key": key,
        "manufacturer_brand": anchor.manufacturer,
        "size_value": anchor.size[0] if anchor.size else None,
        "size_unit": anchor.size[1] if anchor.size else None,
        "pack_count": anchor.pack,
        "variant_descriptor": variant_descriptor,
        "display_name": display.name,
        "category": display.category,
        "members": member_payload,
    }


def groups_to_payload(
    groups: dict[str, list[ProductFeatures]],
    *,
    include_singletons: bool = True,
) -> list[dict]:
    """Sort groups deterministically and convert each to a payload dict."""
    out: list[dict] = []
    for key in sorted(groups):
        members = groups[key]
        if not include_singletons and len(members) < 2:
            continue
        out.append(group_to_payload(key, members))
    return out
