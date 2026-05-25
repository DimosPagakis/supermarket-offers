# Supermarket Offers

Aggregator for Greek supermarket weekly offers. Crawls public chain websites, normalizes products, tracks price history.

> **MVP-lean**: bloat-free, fast iteration. Add complexity via migrations only when needed.

## Architecture

Two services, clean separation. Crawler is dumb (fetch + parse + ship). Backend owns schema, business logic, scheduling.

```
┌─────────────────┐         ┌──────────────────┐
│  Python Crawler │ ──────▶ │ Laravel Backend  │
│    (Scrapy)     │  HTTP   │   (REST API)     │
└─────────────────┘         └────────┬─────────┘
        ▲                            │
        │ HTTP trigger               ▼
        │                       ┌─────────┐
   Laravel Scheduler            │ SQLite  │  (Postgres later)
                                └─────────┘
```

## Repository layout

```
supermarket-offers/
├── backend/    Laravel 12 API + scheduler (PHP 8.3+)
└── crawler/    Python Scrapy spiders (coming soon)
```

## Data model (5 tables)

| Table          | Purpose                                              |
|----------------|------------------------------------------------------|
| `brands`       | Supermarket chain identity                           |
| `crawl_configs`| 1:1 with brand — strategy, start_url, rate limit, cron |
| `crawl_runs`   | History of every crawl attempt (success/fail)        |
| `products`     | Catalog per brand, future canonical-product unification |
| `offers`       | Time-series price/discount snapshots                 |

## Local dev

```bash
cd backend
cp .env.example .env
composer install
php artisan key:generate
php artisan migrate:fresh --seed
php artisan serve
```

Seeded brands: AB Vassilopoulos, Sklavenitis, Lidl Hellas, My Market, Masoutis.

## Roadmap

- [x] Backend schema + models + Greek brand seeders
- [ ] Crawler ↔ Backend REST contract (auth, bulk push)
- [ ] First Scrapy spider (Lidl — simplest HTML)
- [ ] Laravel scheduler → trigger crawler over HTTP
- [ ] Product normalization + canonical-product unification
- [ ] Public read API + frontend

## License

MIT
