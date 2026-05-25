# ADR 0003 — `max_pages_from_env` helper

## Context

Every spider declares its per-run page cap via the same pattern:

    AB_MAX_PAGES        = int(os.getenv("CRAWLER_MAX_PAGES_AB",        "120"))
    LIDL_MAX_CAMPAIGNS  = int(os.getenv("CRAWLER_MAX_PAGES_LIDL",      "200"))
    MYMARKET_MAX_PAGES  = int(os.getenv("CRAWLER_MAX_PAGES_MYMARKET",  "300"))
    MASOUTIS_MAX_PAGES  = int(os.getenv("CRAWLER_MAX_PAGES_MASOUTIS",  "300"))
    SKLAVENITIS_MAX_PAGES = int(os.getenv("CRAWLER_MAX_PAGES_SKLAVENITIS", "300"))

Five copies of the same logic — the env-var-name convention
(``CRAWLER_MAX_PAGES_<BRAND>``) is implicit, and a bad value silently
crashes with ``int("")``. Adding a 6th spider repeats the pattern a
sixth time.

## Decision

Add `scraper.spiders._config.max_pages_from_env(brand_token, default)`.
Five call sites collapse into one-liners, the env-var naming convention
becomes a property of the helper, and a non-numeric override warns and
falls back to the default instead of crashing the spider at import time.

The helper lives under `scraper/spiders/_config.py` (underscore-prefixed
since it's spider-internal — pipelines and parsers don't need it). It
is deliberately not a `BrandConfig` class: the only setting all five
spiders share is "page cap". Discount thresholds, request delays, the
persisted-query hash, the curl_cffi impersonation profile — these are
genuinely brand-specific and stay as module-level constants where they
read.

## Trade-offs

- **Cost**: one new helper module. One indirection between the spider
  and the env var.
- **Benefit**: five call sites become one-liners; the
  ``CRAWLER_MAX_PAGES_<BRAND>`` naming convention is now enforced by
  the helper; a malformed override (e.g. ``CRAWLER_MAX_PAGES_AB=abc``)
  logs a warning and falls back to the spider-shipped default instead
  of crashing the engine at startup with a ``ValueError``.
- **Not done**: no per-brand config class, no Pydantic settings model,
  no dotenv layering. Two settings worth pulling into one place is not
  yet a config schema — that's tax without a customer.
