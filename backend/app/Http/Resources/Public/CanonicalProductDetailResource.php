<?php

namespace App\Http\Resources\Public;

use App\Http\Resources\Public\Concerns\SerialisesCanonicalCore;
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
    use SerialisesCanonicalCore;

    public function toArray(Request $request): array
    {
        $offers = $this->comparison_offers ?? [];

        return [
            ...$this->canonicalCore(),
            'offers' => $offers,
            'price_savings' => isset($this->price_savings) ? round((float) $this->price_savings, 2) : null,
            'cheapest_brand' => $this->cheapestBrandFromOffers($offers),
        ];
    }

    /**
     * Mirror the list resource's `cheapest_brand` shape using the first
     * entry of the controller's pre-sorted comparison_offers list (offers
     * arrive pre-ordered cheapest first). Returns null when the
     * canonical currently has no offers.
     *
     * @param  array<int, array<string, mixed>>  $offers
     * @return array{id: int, name: string, slug: string}|null
     */
    private function cheapestBrandFromOffers(array $offers): ?array
    {
        $first = $offers[0]['brand'] ?? null;
        if (! is_array($first)) {
            return null;
        }

        return [
            'id' => (int) $first['id'],
            'name' => $first['name'],
            'slug' => $first['slug'],
        ];
    }
}
