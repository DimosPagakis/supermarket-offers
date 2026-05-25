"""Shared spider-runtime config helpers.

The only setting every spider exposes the same way is its per-run page
cap. The pattern is::

    <BRAND>_MAX_PAGES = int(os.getenv("CRAWLER_MAX_PAGES_<BRAND>", "<default>"))

Five copies of that line live across the spider modules. This helper
centralises the env-var-name convention and turns a malformed override
(``CRAWLER_MAX_PAGES_AB=abc``) into a warning + fallback rather than a
``ValueError`` at import time.

Other brand-specific knobs (download delays, the AB persisted-query
hash, the curl_cffi impersonation profile, the Masoutis page-size hint)
remain as module-level constants in their spiders — none of them are
shared, and pulling them into a config class would tax every spider
with extra indirection for a single reader. See ADR 0003.
"""

from __future__ import annotations

import os

from loguru import logger


def max_pages_from_env(brand_token: str, default: int) -> int:
    """Return the per-spider page-cap, honouring ``CRAWLER_MAX_PAGES_<TOKEN>``.

    ``brand_token`` is the upper-case suffix used in the env var, e.g.
    ``"AB"`` → reads ``CRAWLER_MAX_PAGES_AB``. Mirrors the historic
    naming convention every spider already documents in its module
    docstring.

    Returns ``default`` when the env var is unset or carries a
    non-numeric / non-positive value (with a warning in the latter
    cases so a typo doesn't quietly run a 5-page smoke test in
    production).
    """
    env_name = f"CRAWLER_MAX_PAGES_{brand_token}"
    raw = os.getenv(env_name)
    if raw is None or raw == "":
        return default
    try:
        value = int(raw)
    except ValueError:
        logger.warning(
            "{} is not an integer ({!r}); falling back to default {}",
            env_name,
            raw,
            default,
        )
        return default
    if value <= 0:
        logger.warning(
            "{}={} is not positive; falling back to default {}",
            env_name,
            value,
            default,
        )
        return default
    return value
