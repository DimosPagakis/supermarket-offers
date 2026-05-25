"""Step 1 investigation: walk every page of AB's PROMOTION_SEARCH and
classify each product by promotion family.

Saves the *full* concatenated response as a fixture so we don't have to
re-hit the live API to regenerate fresh histograms.

Run with the crawler venv active:
    python scripts/ab_investigate.py
"""

from __future__ import annotations

import json
import sys
import time
from collections import Counter
from pathlib import Path
from urllib.parse import urlencode

import httpx

AB_GRAPHQL_URL = "https://www.ab.gr/api/v1/"
AB_PRODUCTLIST_PERSISTED_HASH = (
    "1c53d86bec1b38b5767f39df2af0949e3bb90ce2a0afa177829d93cf26905800"
)
AB_LAZY_LOAD_COUNT = 10

OUT_FIXTURE = Path(__file__).parent.parent / "tests" / "fixtures" / "ab" / "productlist-all-pages.json"


def build_url(page_number: int, listing_type: str = "PROMOTION_SEARCH",
              category_code: str = "") -> str:
    variables = {
        "productListingType": listing_type,
        "lang": "gr",
        "productCodes": "",
        "categoryCode": category_code,
        "excludedProductCodes": "",
        "brands": "",
        "keywords": "",
        "productTypes": "",
        "lazyLoadCount": AB_LAZY_LOAD_COUNT,
        "pageNumber": page_number,
        "sort": "",
        "searchQuery": "",
        "hideProductsWithoutPromo": False,
        "hideUnavailableProducts": True,
        "maxItemsToDisplay": 0,
        "includePotentialActivatableOffers": True,
    }
    extensions = {
        "persistedQuery": {
            "version": 1,
            "sha256Hash": AB_PRODUCTLIST_PERSISTED_HASH,
        }
    }
    params = {
        "operationName": "ProductList",
        "variables": json.dumps(variables, separators=(",", ":")),
        "extensions": json.dumps(extensions, separators=(",", ":")),
    }
    return AB_GRAPHQL_URL + "?" + urlencode(params)


HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "el-GR,el;q=0.9,en;q=0.7",
    "Referer": "https://www.ab.gr/search/promotions",
    "apollo-require-preflight": "true",
    "x-apollo-operation-name": "ProductList",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
}


def main() -> int:
    all_products: list[dict] = []
    total_pages = None
    with httpx.Client(timeout=30, headers=HEADERS) as client:
        page = 0
        while True:
            r = client.get(build_url(page))
            if r.status_code != 200:
                print(f"page {page}: HTTP {r.status_code}", file=sys.stderr)
                print(r.text[:500], file=sys.stderr)
                return 2
            payload = r.json()
            pl = (payload.get("data") or {}).get("productList") or {}
            if not pl:
                print("no productList; errors=", payload.get("errors"))
                return 2
            products = pl.get("products") or []
            pagination = pl.get("pagination") or {}
            if total_pages is None:
                total_pages = int(pagination.get("totalPages") or 1)
                total_results = int(pagination.get("totalResults") or 0)
                print(f"AB reports totalPages={total_pages}, totalResults={total_results}")
            all_products.extend(products)
            print(f"  page {page}: {len(products)} products", flush=True)
            page += 1
            if page >= total_pages:
                break
            time.sleep(2.0)

    # Persist the full concatenated payload as a fixture for tests.
    snapshot = {
        "data": {
            "productList": {
                "products": all_products,
                "pagination": {
                    "totalPages": total_pages,
                    "totalResults": len(all_products),
                    "pageSize": AB_LAZY_LOAD_COUNT,
                    "currentPage": 0,
                },
            }
        }
    }
    OUT_FIXTURE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FIXTURE.write_text(json.dumps(snapshot, ensure_ascii=False))
    print(f"\nSaved {len(all_products)} products → {OUT_FIXTURE}")

    # ---- Step 1 histogram ----
    bucket = Counter()
    promo_type_pairs = Counter()
    sht_true = 0
    no_promo = 0
    for p in all_products:
        sht = bool((p.get("price") or {}).get("showStrikethroughPrice"))
        promos = p.get("potentialPromotions") or []
        types = {pp.get("promotionType") for pp in promos}
        promo_type_pairs[tuple(sorted(t or "<None>" for t in types))] += 1
        if sht:
            sht_true += 1
            bucket["showStrikethroughPrice=True (real price drop)"] += 1
            continue
        if not promos:
            no_promo += 1
            bucket["no promotion at all"] += 1
            continue
        # Bucket by promotion family (when no strikethrough).
        if any("Buy X Get Percentage Off" in (t or "") for t in types):
            bucket["Buy X Get Percentage Off (no strikethrough)"] += 1
        elif any("Buy X Get Y Free" in (t or "") for t in types):
            bucket["Buy X Get Y Free (multi-buy)"] += 1
        elif any("Plus points" in (t or "") for t in types):
            bucket["X Plus points for Y articles (loyalty only)"] += 1
        else:
            bucket[f"other: {sorted(types)}"] += 1

    print("\n=== Step 1 histogram (PROMOTION_SEARCH) ===")
    for k, v in bucket.most_common():
        print(f"  {v:>5}  {k}")
    print(f"\n  showStrikethroughPrice=True count: {sht_true}")
    print(f"  no-promo (data-shape weirdness):    {no_promo}")
    print(f"  total products fetched:             {len(all_products)}")

    print("\nTop promotionType combinations:")
    for combo, v in promo_type_pairs.most_common(20):
        print(f"  {v:>5}  {combo}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
