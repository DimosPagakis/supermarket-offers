<?php

namespace App\Http\Resources\Public;

use App\Models\Brand;
use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\JsonResource;

/**
 * Public-API brand shape. Deliberately omits crawl config — that's an
 * internal concern that lives on /api/v1/brands for the crawler.
 *
 * @mixin Brand
 */
class BrandResource extends JsonResource
{
    public function toArray(Request $request): array
    {
        return [
            'id' => (int) $this->id,
            'name' => $this->name,
            'slug' => $this->slug,
            'website_url' => $this->website_url,
            'country_code' => $this->country_code,
        ];
    }
}
