"""Tests for scraper.clients.backend.BackendClient.

Uses httpx.MockTransport so no network is touched.
"""

from __future__ import annotations

import json

import httpx
import pytest

from scraper.clients.backend import BackendClient


def _make_client(handler) -> BackendClient:
    transport = httpx.MockTransport(handler)
    return BackendClient(
        base_url="http://backend.test",
        token="secret-token",
        transport=transport,
    )


def test_list_brands_sends_bearer_and_returns_list() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["url"] = str(request.url)
        captured["auth"] = request.headers.get("authorization")
        return httpx.Response(
            200,
            json={"data": [{"id": 1, "name": "Lidl"}]},
        )

    with _make_client(handler) as client:
        brands = client.list_brands()

    assert captured["method"] == "GET"
    assert captured["url"] == "http://backend.test/api/v1/brands"
    assert captured["auth"] == "Bearer secret-token"
    assert brands == [{"id": 1, "name": "Lidl"}]


def test_list_brands_accepts_raw_list_response() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[{"id": 1}])

    with _make_client(handler) as client:
        assert client.list_brands() == [{"id": 1}]


def test_start_run_posts_payload() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["path"] = request.url.path
        captured["body"] = json.loads(request.content)
        return httpx.Response(201, json={"id": 42, "status": "running"})

    with _make_client(handler) as client:
        run = client.start_run(brand_id=1, triggered_by="manual")

    assert captured["method"] == "POST"
    assert captured["path"] == "/api/v1/crawl-runs"
    assert captured["body"] == {"brand_id": 1, "triggered_by": "manual"}
    assert run["id"] == 42


def test_push_offers_posts_batch() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"persisted": 2})

    offers = [
        {"name": "Milk", "price": 1.49, "currency": "EUR", "scraped_at": "2026-05-25T08:00:00Z"},
        {"name": "Bread", "price": 0.99, "currency": "EUR", "scraped_at": "2026-05-25T08:00:00Z"},
    ]

    with _make_client(handler) as client:
        resp = client.push_offers(run_id=42, offers=offers)

    assert captured["path"] == "/api/v1/crawl-runs/42/offers"
    assert captured["body"] == {"offers": offers}
    assert resp == {"persisted": 2}


def test_finish_run_patches_with_status() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["path"] = request.url.path
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"ok": True})

    with _make_client(handler) as client:
        client.finish_run(
            run_id=42,
            status="success",
            offers_found=10,
            offers_persisted=10,
        )

    assert captured["method"] == "PATCH"
    assert captured["path"] == "/api/v1/crawl-runs/42"
    assert captured["body"] == {
        "status": "success",
        "offers_found": 10,
        "offers_persisted": 10,
    }


def test_finish_run_includes_error_message_when_provided() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"ok": True})

    with _make_client(handler) as client:
        client.finish_run(
            run_id=42,
            status="failed",
            offers_found=5,
            offers_persisted=0,
            error_message="boom",
        )

    assert captured["body"]["status"] == "failed"
    assert captured["body"]["error_message"] == "boom"


def test_retries_on_5xx_then_succeeds() -> None:
    calls = {"n": 0}

    def handler(_: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] < 2:
            return httpx.Response(503, json={"error": "unavailable"})
        return httpx.Response(200, json={"data": []})

    with _make_client(handler) as client:
        brands = client.list_brands()

    assert calls["n"] == 2
    assert brands == []


def test_does_not_retry_on_4xx() -> None:
    calls = {"n": 0}

    def handler(_: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(404, json={"error": "not found"})

    with _make_client(handler) as client, pytest.raises(httpx.HTTPStatusError):
        client.list_brands()

    assert calls["n"] == 1
