# Crawler API — v1

The crawler talks to the Laravel backend over a small REST API at `/api/v1/*`.
All endpoints require a Sanctum bearer token with the `crawler:write` ability.

## Auth

Issue a token from the backend host:

```bash
php artisan crawler:token local-dev
# prints something like: 1|abc123def456...
```

Use it as a bearer token:

```bash
export CRAWLER_TOKEN="1|abc123def456..."
export API="http://localhost:8000/api/v1"

curl -s "$API/brands" \
  -H "Authorization: Bearer $CRAWLER_TOKEN" \
  -H "Accept: application/json"
```

Without the token (or with a token lacking the ability) you get `401` / `403`.

## Endpoints

### `GET /api/v1/brands`

List active brands with their crawl config.

```bash
curl -s "$API/brands" \
  -H "Authorization: Bearer $CRAWLER_TOKEN" \
  -H "Accept: application/json"
```

Response (truncated):

```json
{
  "data": [
    {
      "id": 1,
      "name": "AB Vassilopoulos",
      "slug": "ab",
      "website_url": "https://www.ab.gr",
      "country_code": "GR",
      "active": true,
      "crawl_config": {
        "strategy": "scrapy",
        "start_url": "https://www.ab.gr/promotions/leaflet",
        "rate_limit_ms": 2000,
        "respect_robots_txt": true,
        "cache_ttl_seconds": 86400
      }
    }
  ]
}
```

### `POST /api/v1/crawl-runs`

Announce that a crawl is starting. Returns a run id you'll use in subsequent calls.

Body:

```json
{
  "brand_id": 1,
  "triggered_by": "schedule"
}
```

`triggered_by` ∈ `schedule | manual | api`.

```bash
curl -s -X POST "$API/crawl-runs" \
  -H "Authorization: Bearer $CRAWLER_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{"brand_id":1,"triggered_by":"schedule"}'
```

Response (`201 Created`):

```json
{
  "data": {
    "id": 17,
    "brand_id": 1,
    "status": "running",
    "started_at": "2026-05-25T08:00:00+00:00",
    "finished_at": null,
    "offers_found": 0,
    "offers_persisted": 0,
    "error_message": null,
    "triggered_by": "schedule"
  }
}
```

### `POST /api/v1/crawl-runs/{run}/offers`

Bulk-push scraped offers (up to 500 per call). Products are upserted by
`(brand_id, external_id)` when `external_id` is present, otherwise by
`(brand_id, normalized_name)`. One `Offer` row is created per item.

The whole batch is wrapped in a database transaction.

Body:

```json
{
  "offers": [
    {
      "external_id": "SKU-123",
      "name": "Φέτα ΠΟΠ 400γρ",
      "url": "https://www.ab.gr/p/123",
      "image_url": "https://cdn.ab.gr/123.jpg",
      "category": "Τυριά",
      "unit": "pcs",
      "price": "4.99",
      "original_price": "6.49",
      "discount_pct": 23,
      "promo_label": "Κέρδος 23%",
      "promo_type": "strikethrough",
      "currency": "EUR",
      "valid_from": "2026-05-25",
      "valid_to": "2026-05-31",
      "scraped_at": "2026-05-25T08:00:00Z"
    }
  ]
}
```

Field reference:

| Field | Type | Notes |
|---|---|---|
| `external_id` | string\|null | Brand's own SKU. Preferred match key. |
| `name` | string | Required. |
| `url` | string\|null | |
| `image_url` | string\|null | |
| `category` | string\|null | |
| `unit` | string\|null | e.g. `kg`, `l`, `pcs` |
| `price` | decimal | Required. ≥ 0. |
| `original_price` | decimal\|null | |
| `discount_pct` | int 0–100\|null | |
| `promo_label` | string\|null, ≤ 80 chars | Brand-supplied Greek badge text (e.g. `"1+1 δώρο"`). Verbatim; advisory display copy. |
| `promo_type` | string\|null, ≤ 32 chars | One of `strikethrough`, `bxgy_free`, `bxg_percent`, `discount_euros`, `loyalty_points`. |
| `currency` | string len 3 | Defaults to `EUR`. |
| `valid_from` | `Y-m-d`\|null | |
| `valid_to` | `Y-m-d`\|null | |
| `scraped_at` | ISO-8601 datetime | Required. |

```bash
curl -s -X POST "$API/crawl-runs/17/offers" \
  -H "Authorization: Bearer $CRAWLER_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d @offers.json
```

Response (`201 Created`):

```json
{
  "data": {
    "persisted": 47,
    "products_created": 5,
    "products_updated": 42
  }
}
```

### `PATCH /api/v1/crawl-runs/{run}`

Mark a run finished.

Body:

```json
{
  "status": "success",
  "offers_found": 47,
  "offers_persisted": 47,
  "error_message": null
}
```

`status` ∈ `success | failed | partial`.
`offers_persisted` is optional — if omitted the backend derives it by counting
offers linked to the run.

```bash
curl -s -X PATCH "$API/crawl-runs/17" \
  -H "Authorization: Bearer $CRAWLER_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{"status":"success","offers_found":47}'
```

Response (`200 OK`):

```json
{
  "data": {
    "id": 17,
    "brand_id": 1,
    "status": "success",
    "started_at": "2026-05-25T08:00:00+00:00",
    "finished_at": "2026-05-25T08:03:11+00:00",
    "offers_found": 47,
    "offers_persisted": 47,
    "error_message": null,
    "triggered_by": "schedule"
  }
}
```

## Error format

Validation failures return `422` with the standard Laravel shape:

```json
{
  "message": "The offers.0.price must be at least 0.",
  "errors": {
    "offers.0.price": ["The offers.0.price must be at least 0."]
  }
}
```

Missing/expired token → `401`. Token without `crawler:write` ability → `403`.
