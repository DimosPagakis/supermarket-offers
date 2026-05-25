"""Scrapy item pipelines.

Currently only one: BackendPipeline. It validates each item via pydantic,
buffers them in memory, and POSTs in batches to the backend's
/api/v1/crawl-runs/{run_id}/offers endpoint.

Designed to be tolerant of the backend being absent during dev — if
BACKEND_URL or BACKEND_TOKEN is missing, items are simply logged.
"""

from __future__ import annotations

import os
from typing import Any

from loguru import logger
from pydantic import ValidationError
from scrapy import Spider

from scraper.clients.backend import BackendClient
from scraper.items import OfferItem

BATCH_SIZE = 100


class BackendPipeline:
    """Buffer validated offers and push them to the backend in batches."""

    def __init__(self) -> None:
        self.enabled: bool = False
        self.client: BackendClient | None = None
        self.run_id: int | None = None
        self.buffer: list[dict] = []
        self.offers_found: int = 0
        self.offers_persisted: int = 0
        self.error_message: str | None = None

    # --- Scrapy lifecycle ------------------------------------------------------

    def open_spider(self, spider: Spider) -> None:
        backend_url = os.getenv("BACKEND_URL")
        backend_token = os.getenv("BACKEND_TOKEN")

        if not backend_url or not backend_token:
            self.enabled = False
            logger.warning(
                "backend push disabled — items will only be logged "
                "(set BACKEND_URL and BACKEND_TOKEN to enable)"
            )
            return

        brand_id = getattr(spider, "brand_id", None)
        if brand_id is None:
            self.enabled = False
            logger.warning(
                "spider {} has no brand_id attribute — backend push disabled",
                spider.name,
            )
            return

        try:
            self.client = BackendClient(backend_url, backend_token)
            run = self.client.start_run(brand_id=int(brand_id), triggered_by="manual")
            self.run_id = int(run.get("id") or run.get("run_id") or run["data"]["id"])
            self.enabled = True
            logger.info(
                "started crawl run id={} for brand_id={} spider={}",
                self.run_id,
                brand_id,
                spider.name,
            )
        except Exception as exc:  # noqa: BLE001 — we want any error to disable cleanly
            self.enabled = False
            logger.exception("failed to start crawl run: {}", exc)

    def process_item(self, item: Any, spider: Spider) -> Any:
        # Accept either an OfferItem or a plain dict.
        try:
            if isinstance(item, OfferItem):
                offer = item
            else:
                offer = OfferItem.model_validate(dict(item))
        except ValidationError as exc:
            logger.warning("dropping invalid item: {} | item={!r}", exc.errors(), item)
            return item

        self.offers_found += 1
        payload = offer.to_payload()

        if not self.enabled:
            logger.debug("offer (not pushed): {}", payload)
            return item

        self.buffer.append(payload)
        if len(self.buffer) >= BATCH_SIZE:
            self._flush(spider)

        return item

    def close_spider(self, spider: Spider) -> None:
        try:
            if self.enabled and self.buffer:
                self._flush(spider)
        except Exception as exc:  # noqa: BLE001
            self.error_message = str(exc)
            logger.exception("flush on close failed: {}", exc)

        if self.enabled and self.client is not None and self.run_id is not None:
            status = "failed" if self.error_message else "success"
            try:
                self.client.finish_run(
                    run_id=self.run_id,
                    status=status,
                    offers_found=self.offers_found,
                    offers_persisted=self.offers_persisted,
                    error_message=self.error_message,
                )
                logger.info(
                    "finished crawl run id={} status={} found={} persisted={}",
                    self.run_id,
                    status,
                    self.offers_found,
                    self.offers_persisted,
                )
            except Exception as exc:  # noqa: BLE001
                logger.exception("failed to PATCH crawl run finish: {}", exc)
            finally:
                self.client.close()

    # --- Internals -------------------------------------------------------------

    def _flush(self, spider: Spider) -> None:
        if not self.buffer or self.client is None or self.run_id is None:
            return
        batch = self.buffer[:BATCH_SIZE]
        try:
            self.client.push_offers(self.run_id, batch)
            self.offers_persisted += len(batch)
            del self.buffer[: len(batch)]
            logger.info(
                "pushed batch of {} offers (total persisted={})",
                len(batch),
                self.offers_persisted,
            )
        except Exception as exc:  # noqa: BLE001
            self.error_message = str(exc)
            logger.exception(
                "failed to push batch of {} offers: {}", len(batch), exc
            )
            # Re-raise so close_spider can record failure status.
            raise
