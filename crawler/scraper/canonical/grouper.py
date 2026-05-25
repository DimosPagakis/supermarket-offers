"""Group :class:`ProductFeatures` into canonical buckets and shape them
into the payload the backend's ``/api/v1/canonical-products/bulk-upsert``
endpoint expects.

Two grouping strategies live here:

* :func:`build_groups` (Phase 1) — buckets every product with a non-None
  ``canonical_key`` by **exact key identity**. Cheap, deterministic, used
  for the historical merge path.

* :func:`build_groups_with_pairs` (Phase 2) — partitions products by the
  weaker **block key** ``(manufacturer, size, pack)``, then runs union-find
  over pairwise :func:`scraper.canonical.matcher.match_decision` results
  inside each block. When a pair lands in the rule matcher's ambiguous
  band (confidence in ``[review_cosine_floor, auto_merge_floor)``) we fall
  through to a sentence-embedding cosine score and only auto-merge when
  cosine is high enough. Pairs in the cosine ``[review_cosine,
  auto_merge_cosine)`` zone are written to a review queue file for a
  human to inspect.

Both strategies emit the same ``payload`` shape via :func:`group_to_payload`
/ :func:`groups_to_payload` so the bulk-upsert endpoint can't tell which
path produced a given canonical product.
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Iterable

from .extractors import ProductFeatures
from .matcher import match_decision

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Phase 1 — exact-key grouping (kept for back-compat and unit tests).
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Phase 2 — block-keyed pairwise scoring with optional embedding fallback.
# ---------------------------------------------------------------------------


def _block_key(f: ProductFeatures) -> tuple[str, tuple[float, str] | None, int] | None:
    """Coarse key that puts candidate-pair products in the same bucket.

    This is ``canonical_key`` minus the variant slug. Products whose
    manufacturer wasn't detected are returned as None (and excluded).
    """
    if f.manufacturer is None:
        return None
    return (f.manufacturer, f.size, f.pack)


@dataclass
class ReviewPair:
    """One ambiguous pair surfaced for human review."""

    a: ProductFeatures
    b: ProductFeatures
    cosine: float
    rule_confidence: float

    def to_record(self) -> dict[str, Any]:
        return {
            "a_product_id": self.a.product_id,
            "a_brand": self.a.brand_slug,
            "a_name": self.a.name,
            "b_product_id": self.b.product_id,
            "b_brand": self.b.brand_slug,
            "b_name": self.b.name,
            "cosine": round(self.cosine, 4),
            "rule_confidence": round(self.rule_confidence, 4),
        }


@dataclass
class GroupingStats:
    """Counters surfaced at the end of the Phase 2 batch run."""

    products_total: int = 0
    products_with_brand: int = 0
    products_no_candidates: int = 0
    blocks_total: int = 0
    blocks_multi: int = 0
    blocks_skipped_huge: int = 0
    pairs_evaluated: int = 0
    pairs_rule_merged: int = 0
    pairs_embedding_merged: int = 0
    pairs_embedding_dropped: int = 0
    pairs_review_queued: int = 0
    pairs_rule_dropped: int = 0
    review_pairs: list[ReviewPair] = field(default_factory=list)

    def as_dict(self) -> dict[str, int]:
        # Excludes the embedded list of review pairs to keep the dict
        # JSON-serialisable as a simple counter map.
        d = self.__dict__.copy()
        d.pop("review_pairs", None)
        return d


class _DSU:
    """Tiny union-find with per-node "join method" tracking.

    ``join_method[node]`` records how the node was first merged into a
    non-singleton component. Initially every node is its own root with
    method ``None``. The first edge that pulls a node out of singleton-
    status sets the method; later joins of an already-multi component
    don't downgrade ``rule`` to ``embedding``.
    """

    def __init__(self, ids: Iterable[int]):
        self.parent: dict[int, int] = {i: i for i in ids}
        self.size: dict[int, int] = {i: 1 for i in self.parent}
        # Per-node method by which this node entered its current
        # multi-member component.
        self.join_method: dict[int, str | None] = {i: None for i in self.parent}

    def find(self, x: int) -> int:
        # Iterative path compression.
        root = x
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[x] != root:
            self.parent[x], x = root, self.parent[x]
        return root

    def union(self, a: int, b: int, method: str) -> bool:
        """Merge a's and b's components. Returns True if a merge actually
        occurred (they were in different components).

        ``method`` is the edge label ("rule" or "embedding"). For each
        node that transitions from singleton to multi-member as a result
        of this union, we record ``method`` as its join method.
        """
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return False

        # Determine which side(s) are still singletons *before* the merge.
        # Those nodes will get ``method`` written as their join method.
        a_singleton = self.size[ra] == 1
        b_singleton = self.size[rb] == 1

        # Union by size.
        if self.size[ra] < self.size[rb]:
            ra, rb = rb, ra
            a_singleton, b_singleton = b_singleton, a_singleton
        self.parent[rb] = ra
        self.size[ra] += self.size[rb]

        # Singletons just absorbed get this edge's method as their join.
        if a_singleton:
            # The whole component represented by ra had size 1, so it's
            # the same node — set its method.
            if self.join_method[ra] is None:
                self.join_method[ra] = method
        if b_singleton:
            if self.join_method[rb] is None:
                self.join_method[rb] = method

        return True

    def components(self) -> dict[int, list[int]]:
        out: dict[int, list[int]] = defaultdict(list)
        for node in self.parent:
            out[self.find(node)].append(node)
        return out


def _features_block_key_for_group(members: list[ProductFeatures]) -> str:
    """Pick a canonical_key for the merged component.

    Strategy: take the alphabetically-smallest non-None canonical_key
    among members. Every member of a single block shares the
    ``(manufacturer, size, pack)`` triple, so all keys differ only in
    the variant slug — using min() makes the choice deterministic.
    """
    keys = sorted(m.canonical_key for m in members if m.canonical_key is not None)
    if keys:
        return keys[0]
    # Defensive fallback (should not happen — block_key excludes
    # manufacturer=None which is the only way canonical_key is None).
    anchor = members[0]
    return f"{anchor.manufacturer or 'unknown'}:nogroup:nosize:{anchor.pack}"


def build_groups_with_pairs(
    features: Iterable[ProductFeatures],
    *,
    use_embeddings: bool = True,
    auto_merge_cosine: float = 0.95,
    review_cosine: float = 0.85,
    rule_ambiguous_floor: float = 0.40,
    rule_auto_merge_floor: float = 0.95,
    max_block_size: int = 60,
    embedding_model: Any | None = None,
) -> tuple[dict[str, list[ProductFeatures]], GroupingStats]:
    """Phase-2 grouping: block by (manufacturer, size, pack), then
    union-find with rule + optional embedding scoring.

    Returns ``(groups, stats)`` where:

    * ``groups`` maps a stable canonical_key (chosen per component) to
      its member list. Compatible with :func:`groups_to_payload`.
    * ``stats`` is a :class:`GroupingStats` recording counts and the
      review-queue payload.

    The match method by which each member joined its component is stored
    on the stats object via the union-find structure; callers that need
    per-member match_method should use :func:`group_to_payload_pairs`,
    which consumes ``method_by_product_id``.

    Embeddings are encoded once per product in a single batched
    ``model.encode`` call across every product that lives in a
    multi-member block. Re-encoding pairs is forbidden — vectors are
    cached and we do dot-products on L2-normalised vectors for cosine.
    """
    features = list(features)
    stats = GroupingStats()
    stats.products_total = len(features)
    stats.products_with_brand = sum(1 for f in features if f.manufacturer is not None)

    # ---- 1. Block by (manufacturer, size, pack). -----------------------
    blocks: dict[tuple[str, tuple[float, str] | None, int], list[ProductFeatures]] = (
        defaultdict(list)
    )
    for f in features:
        bk = _block_key(f)
        if bk is None:
            continue
        blocks[bk].append(f)
    stats.blocks_total = len(blocks)

    # Singletons (block size == 1) → flow straight through as canonical
    # groups (preserving Phase 1 behaviour). Multi-member blocks get
    # pairwise scoring.
    singleton_pids: set[int] = set()
    multi_blocks: list[list[ProductFeatures]] = []
    for bk, members in blocks.items():
        if len(members) == 1:
            singleton_pids.add(members[0].product_id)
        else:
            stats.blocks_multi += 1
            if len(members) > max_block_size:
                logger.warning(
                    "block %r has %d members; exceeds max_block_size=%d, skipping",
                    bk,
                    len(members),
                    max_block_size,
                )
                stats.blocks_skipped_huge += 1
                # Skipped blocks fall back to Phase-1 exact canonical_key
                # grouping: every member is treated as a singleton block,
                # but exact canonical_key matches still cluster via the
                # caller's downstream merge.
                for m in members:
                    singleton_pids.add(m.product_id)
                continue
            multi_blocks.append(members)
    stats.products_no_candidates = len(singleton_pids)

    # ---- 2. Lazy-load + batch-encode embeddings (once across all blocks).
    embed_cache: dict[int, Any] = {}
    if use_embeddings and multi_blocks:
        try:
            # Local import keeps the optional dependency truly optional.
            import numpy as np  # type: ignore[import-not-found]

            from .embedding_matcher import _load_model
        except ImportError as exc:
            logger.warning(
                "embedding fallback disabled — numpy/sentence-transformers "
                "missing (%s). Falling back to rule-only Phase 2.",
                exc,
            )
            use_embeddings = False
            np = None  # type: ignore[assignment]
        else:
            if embedding_model is None:
                embedding_model = _load_model()
            # Collect every product across all multi-blocks (dedup by pid).
            pid_to_feature: dict[int, ProductFeatures] = {}
            for blk in multi_blocks:
                for f in blk:
                    pid_to_feature.setdefault(f.product_id, f)
            ordered_pids = sorted(pid_to_feature)
            texts = [f"query: {pid_to_feature[pid].name}" for pid in ordered_pids]
            if texts:
                vectors = embedding_model.encode(
                    texts,
                    normalize_embeddings=True,
                    show_progress_bar=False,
                )
                vectors = np.asarray(vectors, dtype="float32")
                for pid, vec in zip(ordered_pids, vectors):
                    embed_cache[pid] = vec

    def _cosine(a: ProductFeatures, b: ProductFeatures) -> float | None:
        va = embed_cache.get(a.product_id)
        vb = embed_cache.get(b.product_id)
        if va is None or vb is None:
            return None
        return float((va * vb).sum())

    # ---- 3. Union-find inside each block ------------------------------
    all_ids: list[int] = [f.product_id for f in features if f.manufacturer is not None]
    dsu = _DSU(all_ids)
    feature_by_pid: dict[int, ProductFeatures] = {
        f.product_id: f for f in features if f.manufacturer is not None
    }

    for members in multi_blocks:
        # Sort for determinism — iteration order of dict-based blocks is
        # already insertion-stable, but we sort by product_id so the
        # union order doesn't depend on upstream paging order.
        members_sorted = sorted(members, key=lambda f: f.product_id)
        n = len(members_sorted)
        for i in range(n):
            a = members_sorted[i]
            for j in range(i + 1, n):
                b = members_sorted[j]
                stats.pairs_evaluated += 1
                dec = match_decision(a, b)
                # Rule auto-merge.
                if dec.same and dec.confidence >= rule_auto_merge_floor:
                    if dsu.union(a.product_id, b.product_id, "rule"):
                        stats.pairs_rule_merged += 1
                    continue
                # Rule rejects with high confidence (variant mismatch) →
                # don't even ask the embedding model. This is the
                # "Nirvana Cookie Dough vs Pistachio" guard: same block,
                # very different variant token sets.
                if not dec.same and dec.confidence >= rule_auto_merge_floor:
                    stats.pairs_rule_dropped += 1
                    continue
                # Rule too uncertain → embedding fallback (if available).
                if dec.confidence < rule_ambiguous_floor:
                    stats.pairs_rule_dropped += 1
                    continue
                if not use_embeddings:
                    stats.pairs_rule_dropped += 1
                    continue
                cosine = _cosine(a, b)
                if cosine is None:
                    stats.pairs_rule_dropped += 1
                    continue
                if cosine >= auto_merge_cosine:
                    if dsu.union(a.product_id, b.product_id, "embedding"):
                        stats.pairs_embedding_merged += 1
                elif cosine >= review_cosine:
                    stats.pairs_review_queued += 1
                    stats.review_pairs.append(
                        ReviewPair(
                            a=a,
                            b=b,
                            cosine=cosine,
                            rule_confidence=dec.confidence,
                        )
                    )
                else:
                    stats.pairs_embedding_dropped += 1

    # ---- 4. Materialise components → groups. --------------------------
    components = dsu.components()
    groups: dict[str, list[ProductFeatures]] = {}
    method_by_pid: dict[int, str] = {}
    for root, pids in components.items():
        comp_features = [feature_by_pid[p] for p in pids]
        # Singletons (size 1) retain rule semantics — they never had an
        # embedding edge, only a self-loop.
        key = _features_block_key_for_group(comp_features)
        # Keys may collide if two components produce the same min key
        # (rare but possible if a block was entirely transitively
        # merged and another component fell back to the same canonical
        # key by coincidence). Append a disambiguator in that case.
        if key in groups:
            key = f"{key}#{root}"
        groups[key] = comp_features
        for pid in pids:
            join = dsu.join_method[pid]
            method_by_pid[pid] = join or "rule"

    # Stash on stats so the caller can do per-member shaping deterministically.
    stats.method_by_product_id = method_by_pid  # type: ignore[attr-defined]
    return groups, stats


# ---------------------------------------------------------------------------
# Payload shaping
# ---------------------------------------------------------------------------


def group_to_payload(
    key: str,
    members: list[ProductFeatures],
    *,
    method_by_product_id: dict[int, str] | None = None,
) -> dict:
    """Convert one (canonical_key, members) bucket into the
    ``canonical-products/bulk-upsert`` payload entry.

    The display name is chosen as the longest member name (most
    descriptive across chains). The variant_descriptor is the title-cased
    join of the canonical variant tokens (deterministic order).

    ``method_by_product_id``: when provided, overrides the default
    ``match_method='rule'`` per member. Use the dict surfaced by
    :func:`build_groups_with_pairs` to label products that joined via
    the embedding fallback.
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
        method = (
            (method_by_product_id or {}).get(m.product_id, "rule")
            if method_by_product_id is not None
            else "rule"
        )
        if method == "embedding":
            # Embedding-joined members get a slightly lower confidence
            # so a downstream reviewer can spot them; ``decision.same``
            # may even be False here (the variant Jaccard is what
            # forced us into the embedding path).
            confidence = 0.90
        else:
            confidence = 1.0 if decision.same else 0.85
        member_payload.append(
            {
                "product_id": m.product_id,
                "confidence": round(confidence, 3),
                "match_method": method,
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
    method_by_product_id: dict[int, str] | None = None,
) -> list[dict]:
    """Sort groups deterministically and convert each to a payload dict."""
    out: list[dict] = []
    for key in sorted(groups):
        members = groups[key]
        if not include_singletons and len(members) < 2:
            continue
        out.append(
            group_to_payload(
                key,
                members,
                method_by_product_id=method_by_product_id,
            )
        )
    return out


# ---------------------------------------------------------------------------
# Review queue helpers
# ---------------------------------------------------------------------------


def write_review_queue(pairs: list[ReviewPair], path: str) -> int:
    """Write the ambiguous-pair queue as JSON-lines. Returns the number
    of records written. Caller is responsible for path setup.
    """
    # Deterministic order: by (a_product_id, b_product_id) so re-running
    # the pipeline doesn't churn the file.
    sorted_pairs = sorted(pairs, key=lambda p: (p.a.product_id, p.b.product_id))
    with open(path, "w", encoding="utf-8") as fh:
        for p in sorted_pairs:
            fh.write(json.dumps(p.to_record(), ensure_ascii=False))
            fh.write("\n")
    return len(sorted_pairs)
