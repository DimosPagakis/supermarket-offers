<?php

namespace App\Http\Resources\Public;

use App\Http\Resources\Public\Concerns\SerialisesCanonicalCore;
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
    use SerialisesCanonicalCore;

    public function toArray(Request $request): array
    {
        return [
            ...$this->canonicalCore(),
            'cheapest_brand' => $this->cheapest_brand ?? null,
        ];
    }
}
