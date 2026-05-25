<?php

namespace App\Http\Resources\Public;

use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\JsonResource;

/**
 * Trivial resource wrapping a single category string. We keep it as a
 * resource (not a plain array) so the public API stays consistent —
 * every collection returned by /api/public/v1/* is a JsonResource
 * collection wrapped in `data`.
 */
class CategoryResource extends JsonResource
{
    public function toArray(Request $request): array
    {
        return [
            'name' => (string) $this->resource,
        ];
    }
}
