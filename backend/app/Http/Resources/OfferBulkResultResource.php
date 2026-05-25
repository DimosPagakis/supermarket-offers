<?php

namespace App\Http\Resources;

use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\JsonResource;

/**
 * Wraps the per-batch summary returned by POST /crawl-runs/{run}/offers.
 *
 * Source array shape:
 *   ['persisted' => int, 'products_created' => int, 'products_updated' => int]
 */
class OfferBulkResultResource extends JsonResource
{
    public function toArray(Request $request): array
    {
        return [
            'persisted' => (int) ($this->resource['persisted'] ?? 0),
            'products_created' => (int) ($this->resource['products_created'] ?? 0),
            'products_updated' => (int) ($this->resource['products_updated'] ?? 0),
        ];
    }
}
