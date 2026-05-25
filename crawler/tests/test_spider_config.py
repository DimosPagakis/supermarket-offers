"""Tests for :func:`scraper.spiders._config.max_pages_from_env`.

The five spiders all pull their per-run page cap through this helper.
The behaviours worth pinning:

  * env unset → caller's default,
  * env set to a positive int → int,
  * env set to garbage → default + warning (no ValueError at import),
  * env set to a non-positive value → default + warning.
"""

from __future__ import annotations

import pytest

from scraper.spiders._config import max_pages_from_env


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "CRAWLER_MAX_PAGES_AB",
        "CRAWLER_MAX_PAGES_LIDL",
        "CRAWLER_MAX_PAGES_MYMARKET",
        "CRAWLER_MAX_PAGES_MASOUTIS",
        "CRAWLER_MAX_PAGES_SKLAVENITIS",
        "CRAWLER_MAX_PAGES_TEST",
    ):
        monkeypatch.delenv(name, raising=False)


def test_returns_default_when_env_unset() -> None:
    assert max_pages_from_env("TEST", default=42) == 42


def test_returns_default_for_empty_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CRAWLER_MAX_PAGES_TEST", "")
    assert max_pages_from_env("TEST", default=42) == 42


def test_returns_parsed_int(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CRAWLER_MAX_PAGES_TEST", "7")
    assert max_pages_from_env("TEST", default=42) == 7


def test_falls_back_on_garbage(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CRAWLER_MAX_PAGES_TEST", "abc")
    # Must not raise — the spiders import at engine startup, a crash here
    # would take the whole run down before parsing a single offer.
    assert max_pages_from_env("TEST", default=42) == 42


def test_falls_back_on_zero_or_negative(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CRAWLER_MAX_PAGES_TEST", "0")
    assert max_pages_from_env("TEST", default=42) == 42

    monkeypatch.setenv("CRAWLER_MAX_PAGES_TEST", "-5")
    assert max_pages_from_env("TEST", default=42) == 42


def test_env_var_naming_follows_documented_convention(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The helper is the source of truth for the env-var naming convention.
    A spider passing ``"AB"`` reads ``CRAWLER_MAX_PAGES_AB``."""
    monkeypatch.setenv("CRAWLER_MAX_PAGES_AB", "999")
    assert max_pages_from_env("AB", default=120) == 999
