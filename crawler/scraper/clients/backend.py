"""Sync HTTP client for the supermarket-offers backend.

Wraps the four endpoints the crawler needs:

    GET    /api/v1/brands
    POST   /api/v1/crawl-runs
    POST   /api/v1/crawl-runs/{run_id}/offers
    PATCH  /api/v1/crawl-runs/{run_id}

Sync (httpx.Client) on purpose: Scrapy pipelines live in non-async land
by default, and this keeps the surface area small for the MVP.
"""

from __future__ import annotations

from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential


def _should_retry(exc: BaseException) -> bool:
    """Retry on network/timeout errors and 5xx HTTP responses. Skip 4xx."""
    if isinstance(exc, (httpx.TransportError, httpx.TimeoutException)):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return 500 <= exc.response.status_code < 600
    return False


_RETRY = retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=lambda retry_state: (
        retry_state.outcome is not None
        and retry_state.outcome.failed
        and _should_retry(retry_state.outcome.exception())  # type: ignore[arg-type]
    ),
)


class BackendClient:
    """Thin wrapper around the planned backend HTTP contract."""

    def __init__(
        self,
        base_url: str,
        token: str,
        *,
        timeout: httpx.Timeout | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        timeout = timeout or httpx.Timeout(connect=10.0, read=30.0, write=30.0, pool=10.0)
        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=timeout,
            transport=transport,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "supermarket-offers-crawler/0.1",
            },
        )

    # --- Context manager sugar -------------------------------------------------

    def __enter__(self) -> BackendClient:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    # --- Internal --------------------------------------------------------------

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        # tenacity-wrapped helper that also raises on 4xx/5xx.
        @_RETRY
        def _do() -> httpx.Response:
            resp = self._client.request(method, path, **kwargs)
            resp.raise_for_status()
            return resp

        return _do()

    # --- Public API ------------------------------------------------------------

    def list_brands(self) -> list[dict]:
        resp = self._request("GET", "/api/v1/brands")
        data = resp.json()
        # Accept either {"data": [...]} (Laravel API resource) or raw list.
        if isinstance(data, dict) and "data" in data:
            return data["data"]
        return data

    def start_run(self, brand_id: int, triggered_by: str = "manual") -> dict:
        resp = self._request(
            "POST",
            "/api/v1/crawl-runs",
            json={"brand_id": brand_id, "triggered_by": triggered_by},
        )
        return resp.json()

    def push_offers(self, run_id: int, offers: list[dict]) -> dict:
        resp = self._request(
            "POST",
            f"/api/v1/crawl-runs/{run_id}/offers",
            json={"offers": offers},
        )
        return resp.json()

    def finish_run(
        self,
        run_id: int,
        status: str,
        offers_found: int,
        offers_persisted: int,
        error_message: str | None = None,
    ) -> dict:
        payload: dict[str, Any] = {
            "status": status,
            "offers_found": offers_found,
            "offers_persisted": offers_persisted,
        }
        if error_message is not None:
            payload["error_message"] = error_message
        resp = self._request("PATCH", f"/api/v1/crawl-runs/{run_id}", json=payload)
        return resp.json()
