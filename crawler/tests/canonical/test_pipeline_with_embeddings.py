"""End-to-end smoke test for the Phase-2 block-keyed pipeline.

We use a deterministic *stub* embedding model so the test runs offline
in CI and so the assertions don't depend on PyTorch/Transformers
versions. The stub returns a vector whose components are a function of
the input text; cosine similarity between two stub vectors is controlled
by which tokens the texts share, so we can craft inputs that land in
each of the four buckets:

  * rule-merge       — same brand + same size + same pack + variant
                        Jaccard >= 0.5 (high confidence).
  * embedding-merge  — same block, variants overlap weakly, but the
                        stub cosine returns ~0.97 (above auto-merge).
  * embedding-review — same block, variants overlap weakly, stub
                        cosine in [0.85, 0.95).
  * embedding-drop   — same block, variants disjoint, stub cosine
                        below 0.85.

The stub is a NumPy ``encode`` callable, mirroring
``sentence_transformers.SentenceTransformer.encode`` semantics.
"""

from __future__ import annotations

import math

import numpy as np

from scraper.canonical.extractors import extract_features
from scraper.canonical.grouper import (
    build_groups_with_pairs,
    groups_to_payload,
)


def _build_stub_model(
    names: list[str],
    pair_cosines: dict[frozenset[str], float],
):
    """Build a stub ``SentenceTransformer.encode``-compatible model.

    Each name gets its own basis axis. For each pair in ``pair_cosines``
    we overwrite one side's vector with ``cos * a + sin * orthogonal``
    so the dot product of the L2-normalised vectors equals the target
    cosine. Each name may participate in at most one pair (so the
    rewrite is unambiguous) — sufficient for the four-bucket fixture
    used by the tests below.
    """
    dim = max(len(names) * 2, 16)
    basis = np.eye(dim, dtype="float32")
    vec: dict[str, np.ndarray] = {n: basis[i].copy() for i, n in enumerate(names)}
    next_axis = len(names)
    for key, c in pair_cosines.items():
        a, b = sorted(key)
        s = math.sqrt(max(0.0, 1.0 - c * c))
        vec[b] = (c * vec[a] + s * basis[next_axis]).astype("float32")
        next_axis += 1

    class _Stub:
        def encode(self, texts, normalize_embeddings=True, show_progress_bar=False):
            out = []
            for t in texts:
                name = t[len("query: "):] if t.startswith("query: ") else t
                out.append(vec[name])
            arr = np.stack(out, axis=0).astype("float32")
            if normalize_embeddings:
                norms = np.linalg.norm(arr, axis=1, keepdims=True)
                norms[norms == 0] = 1
                arr = arr / norms
            return arr

    return _Stub()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def _f(pid, brand, name):
    return extract_features(pid, brand, name)


def test_pipeline_routes_pairs_into_four_buckets():
    """Build a tiny catalogue with one product per bucket and assert
    each one lands in the right place."""

    # --- Rule-merge: same brand+size+pack, variant Jaccard >= 0.5.
    # Sklavenitis upcases, Masoutis writes "γρ" — extractor folds both.
    rule_a = _f(101, "sklavenitis", "MELISSA Σπαγγέτι Χωρίς γλουτένη 400g")
    rule_b = _f(102, "my-market", "Melissa Σπαγγέτι Χωρίς Γλουτένη 400gr")

    # --- Embedding-merge: same block, variant Jaccard in [0.25, 0.5)
    # (rule ambiguous → confidence 0.6), stub says cosine 0.97 → merge.
    # Tokens A={krema, oysos, fresh},  B={krema, light} → ∩=1, ∪=4,
    # jaccard 0.25.
    em_merge_a = _f(201, "sklavenitis", "Barilla Penne Krema Oysos Fresh 500g")
    em_merge_b = _f(202, "my-market", "Barilla Penne Krema Light 500g")

    # --- Embedding-review: ambiguous-band rule, stub cosine 0.90.
    # Tokens A={tuna, oil, wild}, B={tuna, water} → ∩=1, ∪=4, jaccard 0.25.
    em_rev_a = _f(301, "sklavenitis", "Rio-Mare Penne Tuna Oil Wild 3x80g")
    em_rev_b = _f(302, "my-market", "Rio-Mare Penne Tuna Water 3x80g")

    # --- Embedding-drop: ambiguous-band rule, stub cosine 0.50.
    # A={gofreta, banana, fresh}, B={gofreta, salt} → ∩=1, ∪=4, jaccard 0.25.
    em_drop_a = _f(401, "sklavenitis", "Lacta Penne Gofreta Banana Fresh 38g")
    em_drop_b = _f(402, "masoutis", "Lacta Penne Gofreta Salt 38g")

    features = [
        rule_a, rule_b,
        em_merge_a, em_merge_b,
        em_rev_a, em_rev_b,
        em_drop_a, em_drop_b,
    ]

    # Verify the rule matcher sits in the ambiguous band for the three
    # non-rule pairs before we run the pipeline; this guards the test
    # against future variant-token tweaks that would invalidate the
    # fixture.
    from scraper.canonical.matcher import match_decision

    d = match_decision(em_merge_a, em_merge_b)
    assert (not d.same and 0.40 <= d.confidence < 0.95) or d.same is True, (
        f"em-merge fixture must be ambiguous or rule-merged; got {d}"
    )
    d = match_decision(em_rev_a, em_rev_b)
    assert (not d.same and 0.40 <= d.confidence < 0.95) or d.same is True, (
        f"em-review fixture must be ambiguous or rule-merged; got {d}"
    )

    # --- Stub model: each pair returns a known controlled cosine. ---
    pair_cos = {
        # em-merge → cosine 0.97 → embedding auto-merge
        frozenset({em_merge_a.name, em_merge_b.name}): 0.97,
        # em-review → cosine 0.90 → review queue
        frozenset({em_rev_a.name, em_rev_b.name}): 0.90,
        # em-drop → cosine 0.50 → embedding drop
        frozenset({em_drop_a.name, em_drop_b.name}): 0.50,
        # rule-merge pair: stub never consulted, but include for safety.
        frozenset({rule_a.name, rule_b.name}): 0.99,
    }
    stub = _build_stub_model(
        [
            rule_a.name, rule_b.name,
            em_merge_a.name, em_merge_b.name,
            em_rev_a.name, em_rev_b.name,
            em_drop_a.name, em_drop_b.name,
        ],
        pair_cos,
    )

    groups, stats = build_groups_with_pairs(
        features,
        use_embeddings=True,
        auto_merge_cosine=0.95,
        review_cosine=0.85,
        embedding_model=stub,
    )

    # ---- Assertions: each pair lands in the right bucket. ----

    # Rule-merge: Melissa pair is one group.
    melissa_group_pids = None
    for members in groups.values():
        pids = {m.product_id for m in members}
        if 101 in pids:
            melissa_group_pids = pids
            break
    assert melissa_group_pids == {101, 102}

    # Embedding-merge: Barilla pair must be one group.
    barilla_group_pids = None
    for members in groups.values():
        pids = {m.product_id for m in members}
        if 201 in pids:
            barilla_group_pids = pids
            break
    assert barilla_group_pids == {201, 202}, (
        f"em-merge pair must collapse, got {barilla_group_pids}"
    )

    # Embedding-review: Rio Mare pair stays as TWO groups (not merged)
    # but lives in the review queue.
    rio_group_pids = [
        sorted(m.product_id for m in members)
        for members in groups.values()
        if any(m.product_id in (301, 302) for m in members)
    ]
    assert sorted(rio_group_pids) == [[301], [302]], (
        f"em-review pair must NOT auto-merge, got {rio_group_pids}"
    )
    assert stats.pairs_review_queued >= 1
    assert any(
        {p.a.product_id, p.b.product_id} == {301, 302}
        for p in stats.review_pairs
    )

    # Embedding-drop: Lacta pair stays as two groups, NOT in review queue.
    lacta_group_pids = [
        sorted(m.product_id for m in members)
        for members in groups.values()
        if any(m.product_id in (401, 402) for m in members)
    ]
    assert sorted(lacta_group_pids) == [[401], [402]]
    assert not any(
        {p.a.product_id, p.b.product_id} == {401, 402}
        for p in stats.review_pairs
    )

    # Bucket-level counts.
    assert stats.pairs_rule_merged >= 1     # Melissa
    assert stats.pairs_embedding_merged >= 1  # Barilla
    assert stats.pairs_review_queued >= 1     # Rio Mare
    assert stats.pairs_embedding_dropped >= 1  # Lacta


def test_payload_carries_per_member_match_method():
    """When a member joined its component via the embedding edge, the
    payload entry's ``members[i].match_method`` must be 'embedding'.
    Rule-merged members must say 'rule'."""

    rule_a = _f(101, "sklavenitis", "MELISSA Σπαγγέτι Χωρίς γλουτένη 400g")
    rule_b = _f(102, "my-market", "Melissa Σπαγγέτι Χωρίς Γλουτένη 400gr")
    # Ambiguous-band pair (jaccard 0.4) — stub will lift to cosine 0.97.
    em_a = _f(201, "sklavenitis", "Barilla Penne Krema Oysos Fresh 500g")
    em_b = _f(202, "my-market", "Barilla Penne Krema Light 500g")

    features = [rule_a, rule_b, em_a, em_b]

    pair_cos = {
        frozenset({em_a.name, em_b.name}): 0.97,
    }
    stub = _build_stub_model(
        [rule_a.name, rule_b.name, em_a.name, em_b.name], pair_cos
    )

    groups, stats = build_groups_with_pairs(
        features,
        use_embeddings=True,
        auto_merge_cosine=0.95,
        review_cosine=0.85,
        embedding_model=stub,
    )
    method_by_pid = stats.method_by_product_id  # type: ignore[attr-defined]

    payload = groups_to_payload(
        groups,
        include_singletons=False,
        method_by_product_id=method_by_pid,
    )
    # Two multi-member groups: melissa (rule), barilla (embedding).
    methods_per_group: list[set[str]] = []
    for entry in payload:
        methods_per_group.append(
            {m["match_method"] for m in entry["members"]}
        )
    assert {"rule"} in methods_per_group
    assert {"embedding"} in methods_per_group


def test_phase2_without_embeddings_falls_back_to_rule_only():
    """``use_embeddings=False`` must produce only rule-merged groups,
    with no embedding consults, no review queue."""
    rule_a = _f(101, "sklavenitis", "MELISSA Σπαγγέτι Χωρίς γλουτένη 400g")
    rule_b = _f(102, "my-market", "Melissa Σπαγγέτι Χωρίς Γλουτένη 400gr")
    em_a = _f(201, "sklavenitis", "Barilla Penne Krema Oysos Fresh 500g")
    em_b = _f(202, "my-market", "Barilla Penne Krema Light 500g")

    groups, stats = build_groups_with_pairs(
        [rule_a, rule_b, em_a, em_b],
        use_embeddings=False,
    )
    assert stats.pairs_embedding_merged == 0
    assert stats.pairs_review_queued == 0
    # Melissa still merges via rule.
    pid_groups = [
        sorted(m.product_id for m in members) for members in groups.values()
    ]
    assert [101, 102] in pid_groups
    # Barilla pair stays separate.
    assert [201] in pid_groups
    assert [202] in pid_groups


def test_phase2_skips_singleton_blocks():
    """A product with a unique (manufacturer, size, pack) tuple should
    pass through as a singleton without any pair evaluation."""
    only = _f(101, "sklavenitis", "MELISSA Σπαγγέτι Χωρίς γλουτένη 400g")
    groups, stats = build_groups_with_pairs([only], use_embeddings=False)
    assert stats.pairs_evaluated == 0
    assert stats.products_no_candidates == 1
    # And the resulting group exists.
    assert any(101 in [m.product_id for m in members] for members in groups.values())


def test_phase2_groups_deterministic_across_runs():
    """Repeating the same input must produce identical groupings and
    identical method_by_product_id assignments."""
    fs = [
        _f(101, "sklavenitis", "MELISSA Σπαγγέτι Χωρίς γλουτένη 400g"),
        _f(102, "my-market", "Melissa Σπαγγέτι Χωρίς Γλουτένη 400gr"),
        _f(103, "masoutis", "Melissa Σπαγγέτι Χωρίς Γλουτένη 400γρ."),
    ]
    g1, s1 = build_groups_with_pairs(fs, use_embeddings=False)
    g2, s2 = build_groups_with_pairs(fs, use_embeddings=False)

    norm1 = sorted(sorted(m.product_id for m in v) for v in g1.values())
    norm2 = sorted(sorted(m.product_id for m in v) for v in g2.values())
    assert norm1 == norm2
    assert s1.method_by_product_id == s2.method_by_product_id  # type: ignore[attr-defined]


def test_review_queue_file_is_jsonl(tmp_path):
    """Smoke-test the write_review_queue helper: file is JSONL, one
    record per pair, fields match the design spec."""
    from scraper.canonical.grouper import ReviewPair, write_review_queue

    a = _f(301, "sklavenitis", "Rio-Mare Tuna Olive Oil 3x80g")
    b = _f(302, "my-market", "Rio-Mare Τόνος Άκριλο 3x80g")
    pair = ReviewPair(a=a, b=b, cosine=0.90, rule_confidence=0.6)
    path = tmp_path / "review.jsonl"
    n = write_review_queue([pair], str(path))
    assert n == 1
    import json
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert rec["a_product_id"] == 301
    assert rec["b_product_id"] == 302
    assert rec["cosine"] == 0.90
    assert rec["rule_confidence"] == 0.6
    assert rec["a_brand"] == "sklavenitis"
    assert rec["b_brand"] == "my-market"
