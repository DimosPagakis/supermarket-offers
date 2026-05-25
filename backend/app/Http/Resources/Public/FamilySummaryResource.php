<?php

namespace App\Http\Resources\Public;

use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\JsonResource;

/**
 * Public-facing summary of one family on the index endpoint.
 *
 * The underlying "model" is a plain array assembled in
 * {@see \App\Http\Controllers\Api\Public\V1\FamilyController}; we keep
 * the shape on the Resource so the serialisation contract is owned by
 * one file rather than spread across the controller.
 */
class FamilySummaryResource extends JsonResource
{
    public static $wrap = 'data';

    public function toArray(Request $request): array
    {
        /** @var array<string, mixed> $row */
        $row = (array) $this->resource;

        return [
            'key' => $row['key'],
            'manufacturer_brand' => $row['manufacturer_brand'],
            'category' => $row['category'],
            'size_value' => $row['size_value'] !== null ? (float) $row['size_value'] : null,
            'size_unit' => $row['size_unit'],
            'pack_count' => (int) $row['pack_count'],
            'display_name' => $row['display_name'],
            'image_url' => $row['image_url'],
            'variants_count' => (int) $row['variants_count'],
            'brands_count' => (int) $row['brands_count'],
            'min_price' => $row['min_price'] !== null ? (float) $row['min_price'] : null,
            'max_price' => $row['max_price'] !== null ? (float) $row['max_price'] : null,
            'avg_price' => $row['avg_price'] !== null
                ? round((float) $row['avg_price'], 2)
                : null,
            'cheapest_brand' => $row['cheapest_brand'] ?? null,
        ];
    }
}
