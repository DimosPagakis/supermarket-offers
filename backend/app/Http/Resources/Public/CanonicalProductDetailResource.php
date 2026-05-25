<?php

namespace App\Http\Resources\Public;

use App\Models\CanonicalProduct;
use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\JsonResource;

/**
 * Detail-view shape for `/api/public/v1/canonical-products/{id}`.
 *
 * Contains a per-member current-offer block ordered cheapest first —
 * the comparison page's primary payload. Each entry collapses the
 * brand, product and offer triple into a flat, presentational shape so
 * the frontend doesn't have to chase relations.
 *
 * Internal canonicalisation audit fields are deliberately omitted.
 *
 * @mixin CanonicalProduct
 */
class CanonicalProductDetailResource extends JsonResource
{
    public function toArray(Request $request): array
    {
        $offers = $this->comparison_offers ?? [];

        return [
            'id' => (int) $this->id,
            'canonical_key' => $this->canonical_key,
            'manufacturer_brand' => $this->manufacturer_brand,
            'size_value' => $this->size_value !== null ? (float) $this->size_value : null,
            'size_unit' => $this->size_unit,
            'pack_count' => (int) $this->pack_count,
            'variant_descriptor' => $this->variant_descriptor,
            'display_name' => $this->display_name,
            'category' => $this->category,
            'image_url' => $this->image_url,
            'members_count' => (int) $this->members_count,
            'brands_count' => (int) $this->brands_count,
            'offers' => $offers,
            'min_price' => isset($this->min_price) ? (float) $this->min_price : null,
            'max_price' => isset($this->max_price) ? (float) $this->max_price : null,
            'avg_price' => isset($this->avg_price) ? round((float) $this->avg_price, 2) : null,
            'price_savings' => isset($this->price_savings) ? round((float) $this->price_savings, 2) : null,
        ];
    }
}
