<?php

namespace Tests\Feature\Api\Public\V1;

use App\Models\Brand;
use App\Models\Offer;
use App\Models\Product;
use App\Support\StringNormalizer;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Carbon;
use Tests\TestCase;

/**
 * Shared scaffolding for the /api/public/v1 feature tests.
 *
 * The public surface is unauthenticated, so we don't need the
 * authedAsCrawler() helper from ApiTestCase. We do need cheap, inline
 * fixtures (no Eloquent factories exist yet in this repo).
 */
abstract class PublicApiTestCase extends TestCase
{
    use RefreshDatabase;

    protected function makeBrand(array $overrides = []): Brand
    {
        return Brand::create(array_merge([
            'name' => 'AB Vassilopoulos',
            'slug' => 'ab',
            'website_url' => 'https://www.ab.gr',
            'country_code' => 'GR',
            'active' => true,
        ], $overrides));
    }

    protected function makeProduct(Brand $brand, array $overrides = []): Product
    {
        $name = $overrides['name'] ?? 'Φέτα ΠΟΠ 400γρ';

        return Product::create(array_merge([
            'brand_id' => $brand->id,
            'external_id' => 'SKU-'.uniqid(),
            'name' => $name,
            'normalized_name' => StringNormalizer::normalize($name),
            'url' => 'https://www.ab.gr/p/'.uniqid(),
            'image_url' => 'https://cdn.ab.gr/'.uniqid().'.jpg',
            'category' => 'Τυριά',
            'unit' => 'pcs',
        ], $overrides));
    }

    protected function makeOffer(Product $product, array $overrides = []): Offer
    {
        return Offer::create(array_merge([
            'product_id' => $product->id,
            'crawl_run_id' => null,
            'price' => 4.99,
            'original_price' => 6.49,
            'discount_pct' => 23,
            'currency' => 'EUR',
            'valid_from' => Carbon::now()->subDays(1)->toDateString(),
            'valid_to' => Carbon::now()->addDays(7)->toDateString(),
            'scraped_at' => Carbon::now(),
        ], $overrides));
    }
}
