"""Pydantic models for crawler output.

These mirror the backend's planned `/api/v1/crawl-runs/{run_id}/offers`
payload contract. Validation happens in the pipeline before items are
buffered for POST.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class OfferItem(BaseModel):
    """A single offer scraped from a flyer / website."""

    model_config = ConfigDict(populate_by_name=True, str_strip_whitespace=True)

    external_id: str | None = None
    name: str
    url: str | None = None
    image_url: str | None = None
    category: str | None = None
    unit: str | None = None

    price: Decimal
    original_price: Decimal | None = None
    discount_pct: int | None = Field(default=None, ge=0, le=100)

    # Human-readable Greek promo badge text (e.g. "1+1 δώρο", "-30% στα 2",
    # "Κέρδος 15%"). Surfaces verbatim on the frontend; carries the savings
    # narrative for multi-buy deals where the per-unit `price` is the
    # regular shelf price (see scraper/parsers/ab.py family docstring).
    promo_label: str | None = Field(default=None, max_length=80)
    # Structured kind of promotion. Mirrors the backend's PROMO_TYPES enum:
    #   strikethrough | bxgy_free | bxg_percent | discount_euros | loyalty_points
    # Use this for branching client-side logic; use `promo_label` for display.
    promo_type: str | None = Field(default=None, max_length=32)

    currency: str = "EUR"

    valid_from: date | None = None
    valid_to: date | None = None

    scraped_at: datetime

    @field_serializer("price", "original_price")
    def _serialize_decimal(self, value: Decimal | None) -> float | None:
        if value is None:
            return None
        return float(value)

    @field_serializer("valid_from", "valid_to")
    def _serialize_date(self, value: date | None) -> str | None:
        if value is None:
            return None
        return value.isoformat()

    @field_serializer("scraped_at")
    def _serialize_datetime(self, value: datetime) -> str:
        # Backend contract expects ISO 8601 with 'Z' for UTC.
        if value.tzinfo is None:
            return value.isoformat() + "Z"
        return value.isoformat().replace("+00:00", "Z")

    def to_payload(self) -> dict:
        """Dump as the JSON-ready dict expected by the backend."""
        return self.model_dump(mode="json")
