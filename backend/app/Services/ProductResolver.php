<?php

namespace App\Services;

use App\Models\Product;
use App\Support\StringNormalizer;

class ProductResolver
{
    /**
     * Resolve a Product for the given brand & scraped offer payload.
     *
     * Match priority:
     *   1. brand_id + external_id (when present)
     *   2. brand_id + normalized_name (fallback)
     *
     * On every resolve we refresh mutable product attributes (name, url,
     * image_url, category, unit) so the latest crawl is the source of truth.
     *
     * @return array{product: Product, created: bool, updated: bool}
     */
    public function resolve(int $brandId, array $offerData): array
    {
        $externalId = $offerData['external_id'] ?? null;
        $name = (string) $offerData['name'];
        $normalized = StringNormalizer::normalize($name);

        $query = Product::query()->where('brand_id', $brandId);

        $product = null;

        if ($externalId !== null && $externalId !== '') {
            $product = (clone $query)->where('external_id', $externalId)->first();
        }

        if ($product === null) {
            $product = (clone $query)
                ->whereNull('external_id')
                ->where('normalized_name', $normalized)
                ->first();
        }

        $attributes = [
            'name' => $name,
            'normalized_name' => $normalized,
            'url' => $offerData['url'] ?? null,
            'image_url' => $offerData['image_url'] ?? null,
            'category' => $offerData['category'] ?? null,
            'unit' => $offerData['unit'] ?? null,
        ];

        if ($product === null) {
            $product = Product::create(array_merge($attributes, [
                'brand_id' => $brandId,
                'external_id' => $externalId,
            ]));

            return ['product' => $product, 'created' => true, 'updated' => false];
        }

        $dirty = false;
        foreach ($attributes as $key => $value) {
            if ($product->{$key} !== $value) {
                $product->{$key} = $value;
                $dirty = true;
            }
        }

        if ($dirty) {
            $product->save();
        }

        return ['product' => $product, 'created' => false, 'updated' => $dirty];
    }
}
