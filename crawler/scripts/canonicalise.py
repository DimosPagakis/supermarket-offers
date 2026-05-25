"""Phase-1 batch canonicalisation driver.

Pulls every active product via the public offers API, runs the rule-based
extractor pipeline, groups by ``canonical_key``, then POSTs the groupings
to the backend's ``/api/v1/canonical-products/bulk-upsert`` endpoint.

Usage
-----

    python -m scripts.canonicalise [--dry-run]
                                   [--public-url URL]
                                   [--backend-url URL]
                                   [--backend-token TOKEN]
                                   [--min-confidence 0.85]
                                   [--batch-size 200]
                                   [--limit-pages N]
                                   [--summary-samples N]

Defaults match the working-environment described in
``docs/canonicalisation-design.md``: read from ``http://127.0.0.1:8001``,
write to ``http://127.0.0.1:8001`` (the backend API exposes both the
public read side and the authenticated write side on the same port).

Output
------

Prints a stats block:

    products processed       12,101
    manufacturer detected     7,832  (64.7%)
    size detected             8,910  (73.6%)
    pack >= 2                 1,420  (11.7%)
    canonical groups          3,455
       singletons             2,901
       >= 2 members             554
       >= 2 brands             319
       >= 3 brands              19

In dry-run mode (the default when no ``--backend-token`` is given) it
also emits one JSON payload batch to stdout for inspection.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from typing import Any, Iterable

# Allow `python -m scripts.canonicalise` from the crawler/ root.
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_CRAWLER_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
if _CRAWLER_ROOT not in sys.path:
    sys.path.insert(0, _CRAWLER_ROOT)

from scraper.canonical.extractors import ProductFeatures, extract_features  # noqa: E402
from scraper.canonical.grouper import build_groups, groups_to_payload  # noqa: E402

DEFAULT_PUBLIC_URL = "http://127.0.0.1:8001/api/public/v1"
DEFAULT_BACKEND_URL = "http://127.0.0.1:8001/api/v1"


# ---------------------------------------------------------------------------
# Fetch
# ---------------------------------------------------------------------------

def _http_get(url: str, timeout: float = 30.0, *, retries: int = 6) -> dict:
    """GET with exponential backoff on 429 / 5xx.

    The public API rate-limits aggressively (60 req/min by default). Pull
    speed is bounded by Laravel's throttle, not the network, so simply
    retrying is fine.
    """
    delay = 1.0
    for attempt in range(retries):
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code in (429, 502, 503, 504) and attempt < retries - 1:
                time.sleep(delay)
                delay = min(delay * 2.0, 30.0)
                continue
            raise


def iter_products(
    public_url: str,
    *,
    per_page: int = 100,
    limit_pages: int | None = None,
    page_delay: float = 0.6,
) -> Iterable[dict]:
    """Yield every offer row from /offers, paginated.

    The public offers endpoint returns one row per *offer*; the same
    `product` can have multiple offers across runs. We deduplicate
    downstream by product_id. A small inter-page sleep keeps us under
    the Laravel `throttle:api` default of 60 req/min.
    """
    page = 1
    while True:
        qs = urllib.parse.urlencode({"per_page": per_page, "page": page})
        body = _http_get(f"{public_url}/offers?{qs}")
        rows = body.get("data", []) or []
        for o in rows:
            yield o
        meta = body.get("meta", {}) or {}
        last = meta.get("last_page") or 1
        if page >= last:
            return
        if limit_pages and page >= limit_pages:
            return
        page += 1
        if page_delay > 0:
            time.sleep(page_delay)


def collect_features(
    public_url: str,
    *,
    limit_pages: int | None = None,
) -> tuple[list[ProductFeatures], dict]:
    """Pull every offer, deduplicate by product_id, run the extractors.

    Returns (features, stats).
    """
    seen: dict[int, ProductFeatures] = {}
    stats: dict[str, Any] = Counter()

    for offer in iter_products(public_url, limit_pages=limit_pages):
        product = offer.get("product") or {}
        brand = offer.get("brand") or {}
        pid = product.get("id")
        name = product.get("name") or ""
        if not pid or not name:
            continue
        if pid in seen:
            continue

        f = extract_features(
            product_id=int(pid),
            brand_slug=brand.get("slug") or "",
            name=name,
            category=product.get("category"),
        )
        seen[pid] = f
        stats["products"] += 1
        if f.manufacturer is not None:
            stats["with_manufacturer"] += 1
        if f.size is not None:
            stats["with_size"] += 1
        if f.pack >= 2:
            stats["with_pack_ge_2"] += 1
        if f.canonical_key is None:
            stats["skipped_no_brand"] += 1
        else:
            stats["with_canonical_key"] += 1

    return list(seen.values()), dict(stats)


# ---------------------------------------------------------------------------
# Post
# ---------------------------------------------------------------------------


class BulkUpsertError(RuntimeError):
    pass


def post_batch(
    backend_url: str,
    token: str | None,
    groupings: list[dict],
    *,
    timeout: float = 60.0,
) -> dict:
    """POST a batch of groupings to the backend.

    When ``token`` is None, raises BulkUpsertError so the caller can
    catch and fall back to dry-run output.
    """
    if not token:
        raise BulkUpsertError("no backend token — refusing to POST")
    url = backend_url.rstrip("/") + "/canonical-products/bulk-upsert"
    payload = json.dumps({"groupings": groupings}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        raise BulkUpsertError(
            f"POST {url} -> {exc.code} {exc.reason}: {body[:500]}"
        ) from exc


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def summarise_groups(groups: dict[str, list]) -> dict[str, int]:
    n_groups = len(groups)
    sizes = [len(v) for v in groups.values()]
    singletons = sum(1 for n in sizes if n == 1)
    multi = sum(1 for n in sizes if n >= 2)
    cross_2 = 0
    cross_3 = 0
    for members in groups.values():
        brands = {m.brand_slug for m in members}
        if len(brands) >= 2:
            cross_2 += 1
        if len(brands) >= 3:
            cross_3 += 1
    return {
        "groups": n_groups,
        "singletons": singletons,
        "multi": multi,
        "cross_2_brands": cross_2,
        "cross_3_brands": cross_3,
    }


def print_sample_groups(
    groups: dict[str, list],
    *,
    n: int = 10,
    min_brands: int = 2,
) -> None:
    # Sort by (#brands desc, #members desc, key) for stable interesting output.
    ranked = sorted(
        groups.items(),
        key=lambda kv: (
            -len({m.brand_slug for m in kv[1]}),
            -len(kv[1]),
            kv[0],
        ),
    )
    shown = 0
    print()
    print(f"# Sample groups (>= {min_brands} brands, top {n})")
    for key, members in ranked:
        brands = sorted({m.brand_slug for m in members})
        if len(brands) < min_brands:
            continue
        shown += 1
        if shown > n:
            break
        print(f"\n  key={key}")
        print(f"  brands={brands}  members={len(members)}")
        for m in members:
            print(f"    {m.brand_slug:12} p={m.product_id:<6} {m.name}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--public-url", default=DEFAULT_PUBLIC_URL)
    p.add_argument("--backend-url", default=DEFAULT_BACKEND_URL)
    p.add_argument("--backend-token", default=os.environ.get("BACKEND_TOKEN"))
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the JSON payload instead of POSTing it (default when "
        "no --backend-token is provided).",
    )
    p.add_argument("--batch-size", type=int, default=200)
    p.add_argument(
        "--min-confidence",
        type=float,
        default=0.85,
        help="Drop groupings whose anchor confidence falls below this. "
        "Phase 1 always emits 1.0 so this is forward-compat plumbing.",
    )
    p.add_argument("--limit-pages", type=int, default=None,
                   help="Stop pulling offers after N pages (smoke testing).")
    p.add_argument("--summary-samples", type=int, default=10,
                   help="Number of cross-brand sample groups to print.")
    p.add_argument("--no-singletons", action="store_true",
                   help="Drop groups with only one member from the payload.")
    args = p.parse_args(argv)

    dry_run = args.dry_run or not args.backend_token

    print(f"[1/3] fetching products from {args.public_url} ...")
    t0 = time.time()
    features, stats = collect_features(
        args.public_url, limit_pages=args.limit_pages
    )
    t_fetch = time.time() - t0
    n = stats.get("products", 0) or 1

    print(f"      done in {t_fetch:.1f}s — {n} unique products")
    print(f"      manufacturer detected : {stats.get('with_manufacturer', 0):>6}  "
          f"({100 * stats.get('with_manufacturer', 0) / n:.1f}%)")
    print(f"      size detected         : {stats.get('with_size', 0):>6}  "
          f"({100 * stats.get('with_size', 0) / n:.1f}%)")
    print(f"      pack >= 2             : {stats.get('with_pack_ge_2', 0):>6}  "
          f"({100 * stats.get('with_pack_ge_2', 0) / n:.1f}%)")
    print(f"      canonical_key set     : {stats.get('with_canonical_key', 0):>6}  "
          f"({100 * stats.get('with_canonical_key', 0) / n:.1f}%)")
    print(f"      skipped (no brand)    : {stats.get('skipped_no_brand', 0):>6}  "
          f"({100 * stats.get('skipped_no_brand', 0) / n:.1f}%)")

    print()
    print("[2/3] grouping by canonical_key ...")
    groups = build_groups(features)
    gstats = summarise_groups(groups)
    print(f"      groups                : {gstats['groups']:>6}")
    print(f"        singletons          : {gstats['singletons']:>6}")
    print(f"        >= 2 members        : {gstats['multi']:>6}")
    print(f"        >= 2 brands         : {gstats['cross_2_brands']:>6}")
    print(f"        >= 3 brands         : {gstats['cross_3_brands']:>6}")

    print_sample_groups(groups, n=args.summary_samples, min_brands=2)

    print()
    print("[3/3] preparing payload ...")
    payload = groups_to_payload(
        groups, include_singletons=not args.no_singletons
    )
    payload = [g for g in payload if any(
        m["confidence"] >= args.min_confidence for m in g["members"]
    )]
    print(f"      payload entries       : {len(payload)}")

    if dry_run:
        print()
        print("# DRY RUN — first batch JSON below (truncated if huge):")
        first = payload[: args.batch_size]
        print(json.dumps(
            {"groupings": first}, ensure_ascii=False, indent=2,
        )[: 20_000])
        return 0

    # POST in batches.
    posted = 0
    aggregate = Counter()
    for i in range(0, len(payload), args.batch_size):
        chunk = payload[i : i + args.batch_size]
        try:
            resp = post_batch(args.backend_url, args.backend_token, chunk)
        except BulkUpsertError as exc:
            print(f"      batch {i // args.batch_size + 1} failed: {exc}",
                  file=sys.stderr)
            return 2
        posted += len(chunk)
        for k in ("created", "updated", "products_assigned"):
            aggregate[k] += int(resp.get(k, 0) or 0)
        if resp.get("errors"):
            print(f"      batch {i // args.batch_size + 1} errors: "
                  f"{resp['errors'][:3]}", file=sys.stderr)

    print(f"      posted {posted} groupings")
    print(f"      backend totals: {dict(aggregate)}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
