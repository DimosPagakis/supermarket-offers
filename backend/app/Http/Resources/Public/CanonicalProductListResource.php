<?php

namespace App\Http\Resources\Public;

use App\Models\CanonicalProduct;
use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\JsonResource;

/**
 * List-view shape for canonical products on the public read API.
 *
 * The controller decorates the model with derived pricing fields
 * (`min_price`, `max_price`, `avg_price`, `cheapest_brand`) computed
 * from the current offers across members. These come off the model as
 * "additional" dynamic properties — the controller sets them before the
 * resource serialises.
 *
 * Internal canonicalisation audit fields (`canonical_match_confidence`,
 * `canonical_match_method`) live on the product side, not the canonical
 * side, and are not surfaced here.
 *
 * @mixin CanonicalProduct
 */
class CanonicalProductListResource extends JsonResource
{
    public function toArray(Request $request): array
    {
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
            'min_price' => isset($this->min_price) ? (float) $this->min_price : null,
            'max_price' => isset($this->max_price) ? (float) $this->max_price : null,
            'avg_price' => isset($this->avg_price) ? round((float) $this->avg_price, 2) : null,
            'cheapest_brand' => $this->cheapest_brand ?? null,
        ];
    }
}
