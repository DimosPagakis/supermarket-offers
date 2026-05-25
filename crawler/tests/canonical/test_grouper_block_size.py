"""Phase 2.1 regression tests for the ``max_block_size`` over-merge guard.

The motivating bug: blocks of (manufacturer, size, pack) with >8 members
are flavour-rich families (Axe deodorants, Ariel pods). Inside them the
boilerplate-heavy product names defeat the embedding fallback and
union-find amplifies a single false-positive edge into a 30-way merge.

The grouper must:

* default the cap to 8;
* skip pairwise scoring entirely for blocks above the cap (no rule
  merge, no embedding merge, no review queue entries);
* honour an explicit ``max_block_size`` kwarg;
* honour the ``CANONICAL_MAX_BLOCK_SIZE`` env variable;
* let small blocks (≤ cap) keep rule-merging as before.
"""

from __future__ import annotations

import pytest

from scraper.canonical.extractors import extract_features
from scraper.canonical.grouper import (
    DEFAULT_MAX_BLOCK_SIZE,
    build_groups_with_pairs,
)


def _f(pid: int, brand: str, name: str):
    return extract_features(pid, brand, name)


# Nine boilerplate-heavy Axe deodorant SKUs from the same chain — the
# canonical over-merge case from the Phase 2 audit (Axe 150ml block).
# All have manufacturer="axe", size=(150,'ml'), pack=1 → one big block.
AXE_SCENTS = [
    "Marine", "Africa", "Apollo", "Black", "Gold",
    "Dark Temptation", "Wild Pepper", "Cherry Fizz", "Ice Chill",
]


def _axe_block(n: int):
    return [
        _f(1000 + i, "my-market", f"Axe Αποσμητικό Σπρέι {scent} 150ml")
        for i, scent in enumerate(AXE_SCENTS[:n])
    ]


def test_default_cap_is_8() -> None:
    assert DEFAULT_MAX_BLOCK_SIZE == 8


def test_block_above_default_cap_is_skipped() -> None:
    features = _axe_block(9)  # one over the cap
    groups, stats = build_groups_with_pairs(features, use_embeddings=False)

    assert stats.blocks_skipped_huge == 1
    assert stats.pairs_evaluated == 0, (
        "huge blocks must skip pairwise scoring entirely — no false "
        "rule-merges, no embedding consults"
    )
    # Every member flows through as its own component (canonical_key
    # collisions could still cluster downstream, but that requires
    # exact key equality which boilerplate-rich blocks don't produce).
    pids_per_group = sorted(
        sorted(m.product_id for m in members) for members in groups.values()
    )
    assert all(len(g) == 1 for g in pids_per_group), (
        f"huge block must not merge anything; got {pids_per_group}"
    )


def test_block_at_default_cap_is_NOT_skipped() -> None:
    features = _axe_block(8)
    _groups, stats = build_groups_with_pairs(features, use_embeddings=False)

    assert stats.blocks_skipped_huge == 0
    # 8 choose 2 = 28 pairs evaluated. Even though they'll all
    # rule-drop (disjoint variants per Phase 2.1), the scoring loop ran.
    assert stats.pairs_evaluated == 28


def test_explicit_max_block_size_overrides_default() -> None:
    features = _axe_block(5)
    _g, stats = build_groups_with_pairs(
        features, use_embeddings=False, max_block_size=3
    )
    assert stats.blocks_skipped_huge == 1


def test_env_var_overrides_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CANONICAL_MAX_BLOCK_SIZE", "4")
    features = _axe_block(5)
    _g, stats = build_groups_with_pairs(features, use_embeddings=False)
    assert stats.blocks_skipped_huge == 1


def test_explicit_kwarg_wins_over_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CANONICAL_MAX_BLOCK_SIZE", "2")
    features = _axe_block(5)
    # Explicit cap=20 → no skip.
    _g, stats = build_groups_with_pairs(
        features, use_embeddings=False, max_block_size=20
    )
    assert stats.blocks_skipped_huge == 0


def test_bad_env_var_falls_back_to_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CANONICAL_MAX_BLOCK_SIZE", "garbage")
    features = _axe_block(9)
    _g, stats = build_groups_with_pairs(features, use_embeddings=False)
    # Default (8) applies → block of 9 is skipped.
    assert stats.blocks_skipped_huge == 1


def test_small_block_still_rule_merges() -> None:
    """The cap must not break the bread-and-butter cross-chain merge."""
    a = _f(1, "sklavenitis", "MELISSA Σπαγγέτι Χωρίς γλουτένη 400g")
    b = _f(2, "my-market", "Melissa Σπαγγέτι Χωρίς Γλουτένη 400gr")
    c = _f(3, "masoutis", "Melissa Σπαγγέτι Χωρίς Γλουτένη 400γρ.")
    groups, stats = build_groups_with_pairs(
        [a, b, c], use_embeddings=False
    )
    assert stats.blocks_skipped_huge == 0
    assert stats.pairs_rule_merged >= 1
    # Single component containing all three pids.
    assert any(
        {m.product_id for m in members} == {1, 2, 3}
        for members in groups.values()
    )
