"""Smoke tests for the batch driver — exercises the stats/grouping
plumbing without hitting a live backend.
"""

from __future__ import annotations

from scraper.canonical.extractors import extract_features
from scraper.canonical.grouper import build_groups
from scripts.canonicalise import (
    print_sample_groups,
    summarise_groups,
)


SAMPLE_NAMES = [
    (101, "sklavenitis", "MELISSA Σπαγγέτι Χωρίς γλουτένη 400g"),
    (102, "my-market",   "Melissa Σπαγγέτι Χωρίς Γλουτένη 400gr"),
    (103, "masoutis",    "Melissa Σπαγγέτι Χωρίς Γλουτένη 400γρ."),
    (201, "sklavenitis", "PEPSI Cola 1,5lt"),
    (202, "my-market",   "Pepsi Cola 1,5lt"),
    (301, "ab",          "Σάλτσα Siciliana 400g"),  # no brand, skipped
]


def test_summarise_groups_counts_brand_breadth():
    features = [extract_features(pid, b, n) for pid, b, n in SAMPLE_NAMES]
    groups = build_groups(features)
    stats = summarise_groups(groups)
    assert stats["groups"] == 2
    assert stats["multi"] == 2
    assert stats["cross_2_brands"] == 2
    assert stats["cross_3_brands"] == 1  # only Melissa spans 3


def test_print_sample_groups_runs_without_error(capsys):
    features = [extract_features(pid, b, n) for pid, b, n in SAMPLE_NAMES]
    groups = build_groups(features)
    print_sample_groups(groups, n=5, min_brands=2)
    out = capsys.readouterr().out
    assert "melissa:" in out
    assert "Sample groups" in out
