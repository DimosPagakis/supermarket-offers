# Public Read API — `/api/public/v1/*`

A read-only HTTP/JSON surface over Greek supermarket offers, served by
the Laravel backend. Built for two audiences from day one:

1. Our own Next.js frontend.
2. Third-party developers building products on top of our data.

There is **no separate enterprise tier**, no API key, no auth. Throttling
is by client IP only (see [Rate limits](#rate-limits)).

For the internal crawler-write contract (`/api/v1/*`, Sanctum PAT) see
`docs/api.md`. The two surfaces are deliberately separate and evolve on
independent schedules.

---

## Stability promise

`/api/public/v1/*` is the long-lived versioned contract. We will ship a
sibling `/api/public/v2/*` before we ever break a `v1` response shape or
remove a field. Additive changes (new optional fields, new endpoints,
new query parameters) can happen on `v1` without a major bump — clients
should ignore unknown keys.

---

## Base URL

| Environment | URL |
|---|---|
| Local dev (this repo) | `http://localhost:8001/api/public/v1` |
| Production | TBD |

The examples below assume:

```bash
export API="http://localhost:8001/api/public/v1"
```

Pick a different port (`php artisan serve --port=8005`) if `:8001`
is in use locally — every example just needs `$API` re-exported.

---

## Rate limits

| Endpoint group | Limit |
|---|---|
| `GET /api/public/v1/*` | **120 requests / minute / IP** |

When you exceed the budget you get `429 Too Many Requests` with
`Retry-After` set to the seconds remaining in the current window. Cache
locally where you can; categories rarely change, brands change even
less often.

CORS is enabled for all origins on `/api/public/*` — you can hit it
straight from a browser without proxying.

---

## Response envelope

Every list endpoint returns:

```json
{
  "data": [ /* resource objects */ ],
  "meta": {
    "current_page": 1,
    "per_page": 50,
    "total": 9047,
    "last_page": 181
  },
  "links": {
    "first": "http://.../offers?page=1",
    "last":  "http://.../offers?page=181",
    "prev":  null,
    "next":  "http://.../offers?page=2",
    "self":  "http://.../offers"
  }
}
```

Single-resource endpoints return `{ "data": { ... } }`.

Errors follow the standard Laravel validation envelope:

```json
{
  "message": "The given data was invalid.",
  "errors": { "per_page": ["The per_page must not be greater than 100."] }
}
```

| Status | Meaning |
|---|---|
| `200 OK` | Successful read |
| `404 Not Found` | Unknown id / slug |
| `422 Unprocessable Entity` | Bad query parameter (range, format, unknown key) |
| `429 Too Many Requests` | Throttle tripped |
| `5xx` | Server error — safe to retry with backoff |

---

## Endpoints

### `GET /brands`

Lists active brands. Five rows; no pagination.

```bash
curl -s "$API/brands"
```

Response:

```json
{
  "data": [
    {
      "id": 1,
      "name": "AB Vassilopoulos",
      "slug": "ab",
      "website_url": "https://www.ab.gr",
      "country_code": "GR"
    }
  ]
}
```

The internal `active` flag and crawl-config metadata are deliberately
omitted from this surface.

---

### `GET /categories`

Distinct, non-null product categories across active brands. Cached for
**1 hour** server-side; expect lag right after a fresh crawl.

```bash
curl -s "$API/categories"
```

```json
{
  "data": [
    { "name": "Τυριά" },
    { "name": "Φρέσκα" }
  ]
}
```

---

### `GET /offers`

The main feed. Returns **one offer per product** — the latest by
`scraped_at` among rows that match every active filter. Filters apply
to the candidate set first, then the latest-per-product collapse picks
the row to surface. So e.g. `min_discount=20&valid_on=2026-05-25`
returns "products with their most recent offer that was ≥20% off and
valid today".

#### Query parameters

| Parameter | Type | Default | Notes |
|---|---|---|---|
| `brand` | csv of slugs | — | e.g. `ab,lidl,masoutis`. |
| `category` | string | — | Case-insensitive exact match. |
| `min_discount` | int 0–100 | — | Keeps `discount_pct >= min_discount`. |
| `has_discount` | bool | — | `true` → only offers where `original_price > price`. |
| `valid_on` | `YYYY-MM-DD` | today | NULL bounds in the offer are treated as open. |
| `q` | string | — | LIKE-match against `products.normalized_name` (Greek accents stripped). |
| `sort` | `discount_pct \| price \| scraped_at` | `discount_pct` | |
| `dir` | `asc \| desc` | `desc` | |
| `page` | int ≥1 | 1 | |
| `per_page` | int 1–100 | 50 | |

Unknown query parameters return `422` so client typos are caught early.

```bash
# Top discounts across AB and Lidl, valid today.
curl -s "$API/offers?brand=ab,lidl&min_discount=20"

# Greek-accent-insensitive search.
curl -s "$API/offers?q=$(printf '%s' 'φέτα' | jq -sRr @uri)"

# Cheapest 50 offers in the cheese category right now.
curl -s "$API/offers?category=$(printf '%s' 'Τυριά' | jq -sRr @uri)&sort=price&dir=asc"
```

A real response item (truncated to one row):

```json
{
  "data": [
    {
      "id": 1,
      "price": 6.08,
      "original_price": 7.15,
      "discount_pct": 15,
      "promo_label": "Κέρδος 15%",
      "promo_type": "strikethrough",
      "currency": "EUR",
      "valid_from": "2026-05-25",
      "valid_to": "2026-06-03",
      "scraped_at": "2026-05-25T11:11:56+00:00",
      "product": {
        "id": 1,
        "external_id": "AB-7606160",
        "name": "Φέτα ΠΟΠ 400γρ",
        "url": "https://www.ab.gr/p/7606160",
        "image_url": "https://www.ab.gr/i/7606160.jpg",
        "category": "Φρέσκα",
        "unit": "400γρ"
      },
      "brand": {
        "id": 1,
        "name": "AB Vassilopoulos",
        "slug": "ab",
        "website_url": "https://www.ab.gr",
        "country_code": "GR"
      }
    }
  ],
  "meta": { "current_page": 1, "per_page": 50, "total": 1, "last_page": 1 },
  "links": {
    "first": "http://localhost:8001/api/public/v1/offers?page=1",
    "last":  "http://localhost:8001/api/public/v1/offers?page=1",
    "prev":  null,
    "next":  null,
    "self":  "http://localhost:8001/api/public/v1/offers"
  }
}
```

---

### `GET /offers/{id}`

Single offer with full product + brand. Pass `?include_history=true` to
attach the price history for the same product across crawl runs,
ordered `scraped_at` desc and capped at 200 entries.

```bash
curl -s "$API/offers/1?include_history=true"
```

```json
{
  "data": {
    "id": 1,
    "price": 6.08,
    "original_price": 7.15,
    "discount_pct": 15,
    "currency": "EUR",
    "valid_from": "2026-05-25",
    "valid_to": "2026-06-03",
    "scraped_at": "2026-05-25T11:11:56+00:00",
    "product": { "id": 1, "name": "Φέτα ΠΟΠ 400γρ", "...": "..." },
    "brand": { "id": 1, "slug": "ab", "...": "..." },
    "history": [
      { "id": 1, "price": 6.08, "original_price": 7.15, "discount_pct": 15, "currency": "EUR", "scraped_at": "2026-05-25T11:11:56+00:00" }
    ]
  }
}
```

---

### `GET /brands/{slug}/offers`

Sugar for `/offers?brand={slug}`. Same query parameters apply
(`category`, `min_discount`, `sort`, etc.). Returns `404` if the slug
doesn't match an active brand.

```bash
curl -s "$API/brands/ab/offers?sort=price&dir=asc"
```

---

### Canonical products

Canonical products are cross-chain SKU groupings — one row per physical
product, with each chain's `products` row attached as a "member".
They power the comparison feature: pick a canonical, see every chain
that stocks it, sorted by price.

The grouping is computed offline by the canonicalisation algorithm
(see `docs/canonicalisation-design.md`) and pushed in via the
authenticated `/api/v1/canonical-products/bulk-upsert` endpoint. The
public read endpoints below surface the read side.

`brands_count` is the number of distinct chains that carry the
canonical — the list view defaults to `min_brands=2` so the response
is comparison-meaningful (a canonical only one chain stocks has
nothing to compare against). `min_price` / `max_price` / `avg_price`
are computed from the latest current offer of each member at request
time, so they always reflect what the comparison page would show.
`cheapest_brand` on the list view points at the brand currently
holding the lowest price — the same brand the detail view's first
offer row will name.

---

### `GET /canonical-products`

#### Query parameters

| Parameter | Type | Default | Notes |
|---|---|---|---|
| `q` | string | — | Case-insensitive LIKE on `display_name`. |
| `brand` | csv of slugs | — | Filters to canonicals with ≥1 member in any of these brands. |
| `category` | string | — | Case-insensitive exact match. |
| `min_brands` | int 1–10 | 2 | Only canonicals with `brands_count >= min_brands`. |
| `sort` | `members_count \| brands_count \| display_name` | `brands_count` | |
| `dir` | `asc \| desc` | `desc` | |
| `page` | int ≥1 | 1 | |
| `per_page` | int 1–100 | 50 | |

```bash
# Default: multi-brand canonicals, most-compared first.
curl -s "$API/canonical-products"

# Text search + category filter.
curl -s "$API/canonical-products?q=Lacta&category=$(printf '%s' 'Σοκολάτες' | jq -sRr @uri)"

# Show every canonical, including single-brand ones (admin-style view).
curl -s "$API/canonical-products?min_brands=1&sort=display_name&dir=asc"
```

A single response row:

```json
{
  "id": 1,
  "canonical_key": "lacta:gofreta-foundouki:31g:1",
  "manufacturer_brand": "Lacta",
  "size_value": 31,
  "size_unit": "g",
  "pack_count": 1,
  "variant_descriptor": "Φουντούκι",
  "display_name": "Lacta Γκοφρέτα Φουντούκι 31g",
  "category": "Σοκολάτες",
  "image_url": "https://cdn.example/lacta.jpg",
  "members_count": 2,
  "brands_count": 2,
  "min_price": 1.1,
  "max_price": 1.2,
  "avg_price": 1.15,
  "cheapest_brand": { "id": 2, "name": "Sklavenitis", "slug": "sklavenitis" }
}
```

---

### `GET /canonical-products/{id}`

The full comparison view — every chain that stocks the canonical,
with the current offer for each, sorted cheapest first.

```bash
curl -s "$API/canonical-products/1"
```

```json
{
  "data": {
    "id": 1,
    "canonical_key": "lacta:gofreta-foundouki:31g:1",
    "manufacturer_brand": "Lacta",
    "size_value": 31,
    "size_unit": "g",
    "pack_count": 1,
    "variant_descriptor": "Φουντούκι",
    "display_name": "Lacta Γκοφρέτα Φουντούκι 31g",
    "category": "Σοκολάτες",
    "image_url": "https://cdn.example/lacta.jpg",
    "members_count": 2,
    "brands_count": 2,
    "offers": [
      {
        "brand": { "id": 2, "name": "Sklavenitis", "slug": "sklavenitis", "country_code": "GR" },
        "product": { "id": 2, "name": "Lacta Γκοφρέτα 31gr", "url": "https://...", "image_url": "https://..." },
        "offer": { "id": 12, "price": 1.10, "original_price": 1.40, "discount_pct": 21, "valid_from": null, "valid_to": null, "scraped_at": "2026-05-25T13:05:16+00:00" }
      },
      {
        "brand": { "id": 1, "name": "AB Vassilopoulos", "slug": "ab", "country_code": "GR" },
        "product": { "id": 1, "name": "LACTA Γκοφρέτα 31g", "url": "https://...", "image_url": "https://..." },
        "offer": { "id": 11, "price": 1.20, "original_price": null, "discount_pct": null, "valid_from": null, "valid_to": null, "scraped_at": "2026-05-25T13:05:16+00:00" }
      }
    ],
    "min_price": 1.10,
    "max_price": 1.20,
    "avg_price": 1.15,
    "price_savings": 0.10
  }
}
```

Notes on detail-view semantics:

- One offer per member product (latest by `id`). The detail view filters
  out offers whose `valid_to` has elapsed; a canonical whose only member
  offers have expired returns `offers: []` and null pricing fields.
- `price_savings = max_price - min_price` — the headline "save up to X€"
  number for the comparison page.
- `404` if the id doesn't exist. There is no brand-scoped sugar for
  canonicals (one canonical spans all brands by definition).

---

### `GET /search?q=…`

Alias of `/offers?q=…`. `q` is required.

```bash
curl -s "$API/search?q=$(printf '%s' 'φέτα' | jq -sRr @uri)"
```

Useful when building a search-first UI: keeps the URL semantic
(`/search?q=...` reads better than `/offers?q=...`).

---

## Greek text — search semantics

Product names are stored both as-crawled (`products.name`) and in a
normalised form (`products.normalized_name`) that is lowercased and
stripped of Greek diacritics. The `q` filter compares against
`normalized_name`, so:

- `q=feta`, `q=φετα`, `q=Φέτα`, `q=ΦΕΤΑ` — all match `"Φέτα ΠΟΠ 400γρ"`.
- `category=Τυριά` and `category=τυριά` — both match the curated
  category string.

We do not perform accent normalisation on `category` because category
strings come from a small curated set per brand; if your filter doesn't
match, hit `/categories` to see the exact spelling.

---

## Promo label & promo type

Every `offer` payload now carries two optional fields alongside the
existing numeric pricing columns:

| Field | Type | Notes |
|---|---|---|
| `promo_label` | `string \| null`, ≤ 80 chars | **Advisory display copy** — the brand-supplied Greek badge text the shopper sees on the brand's own page (e.g. `"1+1 δώρο"`, `"-30% στα 2"`, `"Κέρδος 15%"`). Render verbatim — do not parse. |
| `promo_type` | `string \| null`, ≤ 32 chars | **Structured kind** of promotion. One of `strikethrough`, `bxgy_free`, `bxg_percent`, `discount_euros`, `loyalty_points`. Use this to branch UI / filtering logic. |

For `strikethrough` deals the `price` column is the real per-unit
discounted shelf price (legacy behaviour). For `bxgy_free`,
`bxg_percent` and `discount_euros` the `price` is the **regular shelf
price** — the multi-buy maths only applies if the shopper buys the
qualifying basket, so we deliberately do not pretend the per-unit
effective price is what they will see at the till. `original_price`
and `discount_pct` are typically null for those families; the
`promo_label` carries the savings narrative.

Both fields are nullable and additive. Clients written against the
pre-promo-label contract see `null` and continue to work; they just
miss the richer label rendering. New clients should prefer
`promo_label` over the numeric `discount_pct` when both are set —
brand-supplied copy is more precise than our reconstruction.

---

## What's *not* in the public response

We hide ingestion plumbing from the public surface so a future schema
change in the crawler ingest path doesn't leak through. The following
internal fields are filtered out:

- `crawl_run_id`, `offers_persisted`, `offers_found`
- `Brand.active` (the public list only ever contains active brands)
- `crawl_config` (strategy, start_url, rate limit, robots policy)
- `Product.normalized_name` and `Product.canonical_product_id`
- All `created_at` / `updated_at` timestamps

If you need any of these for a legitimate use case, file an issue —
we'd rather extend the public schema deliberately than have clients
scrape internal fields from the crawler-write API.

---

## Versioning / deprecation

Breaking changes go to `/api/public/v2`. Until that ship, we promise:

- We will not rename or remove a field in the `v1` response.
- We will not change the type of a `v1` field.
- We will not tighten a `v1` query-parameter validation rule in a way
  that turns previously valid requests into `422`s.

We may add new optional query parameters, new fields, new endpoints,
and new sort options. Clients should ignore unknown keys.

When `v2` ships we will announce a deprecation window of at least 90
days in this document before `v1` is retired.

---

## No OpenAPI yet

We've intentionally not shipped an OpenAPI spec — the surface is small
enough that the markdown above is the contract, and YAML maintenance
costs MVP velocity. If you need one, the feature tests in
`tests/Feature/Api/Public/V1/` describe every shape and edge case end
to end; reading them is faster than reading a spec.
