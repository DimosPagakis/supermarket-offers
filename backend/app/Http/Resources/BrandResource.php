<?php

namespace App\Http\Resources;

use App\Models\Brand;
use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\JsonResource;

/**
 * @mixin Brand
 */
class BrandResource extends JsonResource
{
    public function toArray(Request $request): array
    {
        $config = $this->whenLoaded('crawlConfig');

        return [
            'id' => $this->id,
            'name' => $this->name,
            'slug' => $this->slug,
            'website_url' => $this->website_url,
            'country_code' => $this->country_code,
            'active' => (bool) $this->active,
            'crawl_config' => $config && $this->crawlConfig ? [
                'strategy' => $this->crawlConfig->strategy,
                'start_url' => $this->crawlConfig->start_url,
                'rate_limit_ms' => (int) $this->crawlConfig->rate_limit_ms,
                'respect_robots_txt' => (bool) $this->crawlConfig->respect_robots_txt,
                'cache_ttl_seconds' => (int) $this->crawlConfig->cache_ttl_seconds,
            ] : null,
        ];
    }
}
