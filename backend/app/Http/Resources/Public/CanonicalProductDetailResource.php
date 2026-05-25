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

        // Derive cheapest_brand from the comparison_offers payload — same
        // shape the list resource exposes, so the frontend can rely on
        // both endpoints carrying it. Offers are pre-ordered cheapest
        // first by the controller, so the first entry's brand wins. If
        // the list is empty we leave it null and the UI handles that.
        $cheapestBrand = null;
        if (!empty($offers)) {
            $first = $offers[0]['brand'] ?? null;
            if (is_array($first)) {
                $cheapestBrand = [
                    'id' => (int) $first['id'],
                    'name' => $first['name'],
                    'slug' => $first['slug'],
                ];
            }
        }

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
            'cheapest_brand' => $cheapestBrand,
        ];
    }
}
