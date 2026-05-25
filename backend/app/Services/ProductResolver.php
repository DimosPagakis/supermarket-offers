<?php

namespace App\Services;

use App\Models\Product;
use App\Support\StringNormalizer;

class ProductResolver
{
    public function __construct(private readonly VariantDescriber $describer = new VariantDescriber()) {}

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
     * Family-browse feature columns (`manufacturer_brand`,
     * `category_normalised`, `size_value`, `size_unit`, `pack_count`,
     * `variant_descriptor`) are recomputed every pass via
     * {@see VariantDescriber} — they're a pure function of `name` +
     * `category`, so refreshing them keeps the family index in sync
     * with whatever the latest crawl reports. This is cheap (regex on a
     * single string) and saves us from a second job/cron.
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

        $features = $this->describer->extract($name, $offerData['category'] ?? null);

        $attributes = [
            'name' => $name,
            'normalized_name' => $normalized,
            'url' => $offerData['url'] ?? null,
            'image_url' => $offerData['image_url'] ?? null,
            'category' => $offerData['category'] ?? null,
            'unit' => $offerData['unit'] ?? null,
            'manufacturer_brand' => $features['manufacturer_brand'],
            'category_normalised' => $features['category_normalised'],
            'size_value' => $features['size_value'],
            'size_unit' => $features['size_unit'],
            'pack_count' => $features['pack_count'],
            'variant_descriptor' => $features['variant_descriptor'],
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
