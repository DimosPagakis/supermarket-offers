# Supermarket Offers — Crawler

Scrapy crawler that scrapes weekly offers from Greek supermarket flyers and
pushes them to the backend API at `/api/v1/*`.

This is the **MVP skeleton**. Goal: one working spider end-to-end (Lidl),
clean validation + pipeline plumbing, easy to add more brands.

## Stack

- Python 3.12
- [Scrapy](https://scrapy.org/) 2.11+ with `scrapy-playwright` (wired up
  for future JS-heavy targets such as Masoutis and Sklavenitis)
- [pydantic](https://docs.pydantic.dev/) v2 for item validation
- [httpx](https://www.python-httpx.org/) for backend POSTs
  (sync — Scrapy pipelines are sync by default)
- [tenacity](https://tenacity.readthedocs.io/) for retries on backend errors
- [loguru](https://github.com/Delgan/loguru) for logging

## Local setup

```bash
cd crawler
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# For Playwright-based spiders (not needed for Lidl):
python -m playwright install chromium
```

Copy `.env.example` to `.env` and fill in values:

```bash
cp .env.example .env
```

Env vars:

| Variable             | Purpose                                                | Default |
| -------------------- | ------------------------------------------------------ | ------- |
| `BACKEND_URL`        | Base URL of the Laravel backend                        | _none_  |
| `BACKEND_TOKEN`      | Sanctum personal access token (Bearer auth)            | _none_  |
| `LOG_LEVEL`          | Scrapy/loguru log level                                | `INFO`  |
| `HTTPCACHE_ENABLED`  | Set to `1` to cache HTTP responses on disk             | `0`     |
| `DOWNLOAD_DELAY`     | Per-request delay (seconds)                            | `2`     |

If `BACKEND_URL` or `BACKEND_TOKEN` is missing, the pipeline disables itself
and just logs each item. The spider still runs — handy for local iteration.

## Run a spider

```bash
# from crawler/
scrapy crawl lidl
```

To dump items to a JSONL file locally without touching the backend, unset
`BACKEND_TOKEN` and pipe Scrapy's output:

```bash
unset BACKEND_TOKEN
scrapy crawl lidl -O offers.jsonl
```

## Tests

```bash
pytest
```

The test suite covers `scraper.normalize` parsing and the
`BackendClient` HTTP contract (via `httpx.MockTransport` — no network).

## Layout

```
crawler/
├── pyproject.toml          # deps + tooling config
├── Dockerfile              # python:3.12-slim + playwright chromium
├── scrapy.cfg              # Scrapy project descriptor
├── .env.example
├── scraper/
│   ├── settings.py         # robots-on, autothrottle, env-tunable cache
│   ├── items.py            # OfferItem (pydantic)
│   ├── normalize.py        # parse_price / parse_date / parse_date_range
│   ├── pipelines.py        # BackendPipeline — buffer + POST in batches of 100
│   ├── clients/
│   │   └── backend.py      # BackendClient(list_brands/start_run/push/finish)
│   └── spiders/
│       └── lidl.py         # Lidl flyer spider
└── tests/                  # pytest suite
```

## Lidl strategy

`https://www.lidl-hellas.gr/c/fylladio-lidl/s10020481` is the landing page
that lists the current week's flyers (food + non-food). The spider:

1. Loads the landing page.
2. Finds the first anchor whose surrounding text mentions **"Από"** (Greek
   for _"From"_) — Lidl labels each flyer block with its validity start.
3. Follows that link to the flyer detail page.
4. Extracts product cards and yields validated `OfferItem`s.

The spider is **defensive**: if any CSS selector misses, it logs a warning
and yields nothing rather than crashing. Next iteration will tune selectors
against real HTML and add fixtures.

## Roadmap

| Brand            | Status         | Notes                                          |
| ---------------- | -------------- | ---------------------------------------------- |
| Lidl Hellas      | Implemented    | Static HTML — Scrapy only                      |
| AB Vassilopoulos | TODO           | Static HTML — Scrapy only                      |
| Masoutis         | TODO           | JS-heavy — needs `scrapy-playwright`           |
| Sklavenitis      | TODO           | JS-heavy — needs `scrapy-playwright`           |
| Bazaar           | TODO           | Static HTML                                    |
| My Market        | TODO           | TBD                                            |

## Docker

```bash
docker build -t supermarket-offers-crawler .
docker run --rm --env-file .env supermarket-offers-crawler
```

Default command runs `scrapy crawl lidl`.
