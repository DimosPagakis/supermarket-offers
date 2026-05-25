"""End-to-end integration test for the Phase-1 canonicalisation pipeline.

Feeds a frozen sample of real product rows through:
    extract_features → build_groups → groups_to_payload

…and asserts the expected cross-brand merges happen (and the
deliberate non-merges do NOT).

All names below come from the live :8001 DB on 2026-05-25.
"""

from __future__ import annotations

from scraper.canonical.extractors import extract_features
from scraper.canonical.grouper import build_groups, group_to_payload, groups_to_payload

# (product_id, brand_slug, name, category)
SAMPLE: list[tuple[int, str, str, str]] = [
    # Three chains, same SKU — must merge.
    (101, "sklavenitis", "MELISSA Σπαγγέτι Χωρίς γλουτένη 400g", "Ζυμαρικά"),
    (102, "my-market",   "Melissa Σπαγγέτι Χωρίς Γλουτένη 400gr", "Ζυμαρικά"),
    (103, "masoutis",    "Melissa Σπαγγέτι Χωρίς Γλουτένη 400γρ.", "Ζυμαρικά"),

    # Three chains, same Pepsi 1.5L — must merge.
    (201, "sklavenitis", "PEPSI Cola 1,5lt", "Αναψυκτικά"),
    (202, "my-market",   "Pepsi Cola 1,5lt", "Αναψυκτικά"),
    (203, "masoutis",    "Pepsi Cola 1,5lt.", "Αναψυκτικά"),

    # Three chains, Rio Mare 3x80g — must merge.
    (301, "sklavenitis", "RIO MARE Τόνος σε Ελαιόλαδο 3x80g", "Κονσέρβες"),
    (302, "my-market",   "Rio Mare Τόνος Σε Ελαιόλαδο 3x80gr", "Κονσέρβες"),
    (303, "masoutis",    "Rio Mare Τόνος Σε Ελαιόλαδο 3x80γρ.", "Κονσέρβες"),

    # Pampers different sizes — must NOT merge.
    (401, "sklavenitis", "PAMPERS Active Baby Pants Πάνες Βρακάκι Νο6 13-19kg 42τεμ", "Πάνες"),
    (402, "masoutis",    "PAMPERS Active Baby Pants Πάνες Βρακάκι Νο7 17-25kg 38τεμ", "Πάνες"),

    # Nirvana different flavours — must NOT merge.
    (501, "sklavenitis", "NIRVANA Παγωτό Brownies & Salted Caramel 302g (420ml)", "Παγωτά"),
    (502, "masoutis",    "Nirvana Παγωτό Cookie Dough 302γρ./420ml.", "Παγωτά"),

    # Own-brand (My Gusto) — must stay isolated (canonical_key=None).
    (601, "my-market",   "My Gusto Πάριζα & Τυρί Gouda 280gr", "Αλλαντικά"),
]


def _features():
    return [extract_features(pid, slug, name, cat) for pid, slug, name, cat in SAMPLE]


def test_melissa_group_has_three_brands():
    features = _features()
    groups = build_groups(features)

    melissa_groups = [
        (k, m) for k, m in groups.items() if k.startswith("melissa:")
    ]
    assert len(melissa_groups) == 1, melissa_groups
    _, members = melissa_groups[0]
    brand_set = {m.brand_slug for m in members}
    assert brand_set == {"sklavenitis", "my-market", "masoutis"}
    assert {m.product_id for m in members} == {101, 102, 103}


def test_pepsi_group_has_three_brands():
    features = _features()
    groups = build_groups(features)
    pepsi = [m for k, m in groups.items() if k.startswith("pepsi:")]
    assert len(pepsi) == 1
    assert len(pepsi[0]) == 3


def test_rio_mare_group_has_three_brands():
    features = _features()
    groups = build_groups(features)
    rio = [m for k, m in groups.items() if k.startswith("rio-mare:")]
    assert len(rio) == 1
    assert len(rio[0]) == 3


def test_pampers_no6_and_no7_in_separate_groups():
    features = _features()
    groups = build_groups(features)
    pampers = [m for k, m in groups.items() if k.startswith("pampers:")]
    assert len(pampers) == 2  # two groups, not one
    for grp in pampers:
        assert len(grp) == 1


def test_nirvana_flavours_in_separate_groups():
    features = _features()
    groups = build_groups(features)
    nirvana = [m for k, m in groups.items() if k.startswith("nirvana:")]
    assert len(nirvana) == 2  # cookie-dough vs brownies, separate
    for grp in nirvana:
        assert len(grp) == 1


def test_my_gusto_not_grouped():
    """Own-brand products produce no canonical_key and so don't appear in
    `build_groups` output at all."""
    features = _features()
    groups = build_groups(features)
    for key, members in groups.items():
        for m in members:
            assert m.product_id != 601, f"private label leaked into {key}"


def test_payload_shape_for_three_chain_merge():
    features = _features()
    groups = build_groups(features)
    melissa_key = next(k for k in groups if k.startswith("melissa:"))
    payload = group_to_payload(melissa_key, groups[melissa_key])

    assert payload["canonical_key"] == melissa_key
    assert payload["manufacturer_brand"] == "melissa"
    assert payload["size_value"] == 400.0
    assert payload["size_unit"] == "g"
    assert payload["pack_count"] == 1
    assert isinstance(payload["display_name"], str)
    assert payload["category"] == "Ζυμαρικά"
    assert len(payload["members"]) == 3
    for m in payload["members"]:
        assert m["match_method"] == "rule"
        assert 0.0 <= m["confidence"] <= 1.0


def test_groups_to_payload_is_deterministic():
    """Same inputs → byte-identical output (no Python set ordering leaks)."""
    features = _features()
    g1 = build_groups(features)
    g2 = build_groups(features)
    p1 = groups_to_payload(g1)
    p2 = groups_to_payload(g2)
    assert p1 == p2


def test_payload_excluding_singletons():
    features = _features()
    groups = build_groups(features)
    payload_all = groups_to_payload(groups)
    payload_multi = groups_to_payload(groups, include_singletons=False)
    assert len(payload_multi) < len(payload_all)
    for entry in payload_multi:
        assert len(entry["members"]) >= 2


def test_canonical_keys_are_stable_across_runs():
    """Determinism is foundational. If this breaks, every existing
    canonical_product_id in the DB silently goes stale."""
    snapshot = {
        f.product_id: f.canonical_key for f in _features()
    }
    again = {
        f.product_id: f.canonical_key for f in _features()
    }
    assert snapshot == again
