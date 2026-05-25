<?php

namespace App\Http\Resources\Public;

use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\JsonResource;

/**
 * Detail view for /api/public/v1/families/{key}. Surfaces the full
 * variant list (grouped by `variant_descriptor`) and per-variant
 * pricing summary. Shape mirrors the contract documented in the
 * family-browse task brief — keep additive when the contract evolves.
 */
class FamilyDetailResource extends JsonResource
{
    public static $wrap = 'data';

    public function toArray(Request $request): array
    {
        /** @var object $row */
        $row = $this->resource;

        return [
            'key' => $row->key,
            'manufacturer_brand' => $row->manufacturer_brand,
            'category' => $row->category,
            'category_normalised' => $row->category_normalised,
            'size_value' => $row->size_value !== null ? (float) $row->size_value : null,
            'size_unit' => $row->size_unit,
            'pack_count' => (int) $row->pack_count,
            'display_name' => $row->display_name,
            'image_url' => $row->image_url,
            'variants_count' => (int) $row->variants_count,
            'brands_count' => (int) $row->brands_count,
            'min_price' => $row->min_price !== null ? (float) $row->min_price : null,
            'max_price' => $row->max_price !== null ? (float) $row->max_price : null,
            'avg_price' => $row->avg_price !== null
                ? round((float) $row->avg_price, 2)
                : null,
            'variants' => array_map(fn (array $v) => [
                'variant_descriptor' => $v['variant_descriptor'],
                'products' => $v['products'],
                'min_price' => $v['min_price'] !== null ? (float) $v['min_price'] : null,
                'max_price' => $v['max_price'] !== null ? (float) $v['max_price'] : null,
                'cheapest_brand' => $v['cheapest_brand'],
            ], $row->variants),
        ];
    }
}
