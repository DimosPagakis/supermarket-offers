<?php

namespace App\Http\Resources\Public;

use App\Models\Product;
use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\JsonResource;

/**
 * @mixin Product
 */
class ProductResource extends JsonResource
{
    public function toArray(Request $request): array
    {
        return [
            'id' => (int) $this->id,
            'external_id' => $this->external_id,
            'name' => $this->name,
            'url' => $this->url,
            'image_url' => $this->image_url,
            'category' => $this->category,
            'unit' => $this->unit,
        ];
    }
}
