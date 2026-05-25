<?php

namespace App\Http\Resources\Public\Concerns;

/**
 * Shared serialiser for the canonical-product fields that the list and
 * detail resources both expose.
 *
 * The public API treats the canonical core (identity + descriptive
 * fields + member/brand counts + derived pricing) as a stable shape;
 * both views start from it and add their own extras (cheapest_brand on
 * the list, offers + price_savings on the detail). Keeping the shared
 * fields in one place is how we guarantee they stay byte-identical
 * across endpoints — the public contract documented in
 * docs/public-api.md depends on it.
 */
trait SerialisesCanonicalCore
{
    /**
     * @return array<string, mixed>
     */
    protected function canonicalCore(): array
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
        ];
    }
}
