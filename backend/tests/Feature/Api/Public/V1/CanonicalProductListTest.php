<?php

namespace Tests\Feature\Api\Public\V1;

use App\Models\Brand;
use App\Models\CanonicalProduct;
use App\Models\Product;

class CanonicalProductListTest extends PublicApiTestCase
{
    /**
     * Create one canonical with N members, one per supplied brand slug.
     * Each member also gets a current offer at the supplied price.
     */
    private function seedCanonical(
        string $canonicalKey,
        string $displayName,
        array $brandPrices,
        string $manufacturerBrand = 'Lacta',
        ?string $category = 'Σοκολάτες',
    ): CanonicalProduct {
        $canonical = CanonicalProduct::create([
            'canonical_key' => $canonicalKey,
            'manufacturer_brand' => $manufacturerBrand,
            'display_name' => $displayName,
            'category' => $category,
            'size_value' => 31.0,
            'size_unit' => 'g',
            'pack_count' => 1,
            'image_url' => 'https://cdn.example/'.$canonicalKey.'.jpg',
        ]);

        foreach ($brandPrices as $slug => $price) {
            $brand = Brand::firstWhere('slug', $slug)
                ?? $this->makeBrand([
                    'slug' => $slug,
                    'name' => strtoupper($slug),
                    'website_url' => "https://www.{$slug}.gr",
                ]);
            $product = $this->makeProduct($brand, [
                'name' => $displayName.' @ '.$slug,
                'normalized_name' => mb_strtolower($displayName.' @ '.$slug),
                'canonical_product_id' => $canonical->id,
                'canonical_match_confidence' => 1.0,
                'canonical_match_method' => 'rule',
                'canonical_matched_at' => now(),
            ]);
            $this->makeOffer($product, ['price' => $price]);
        }

        $canonical->refreshAggregates();

        return $canonical;
    }

    public function test_happy_path_returns_paginated_envelope(): void
    {
        $this->seedCanonical('a', 'Product A', ['ab' => 1.0, 'lidl' => 1.1]);

        $response = $this->getJson('/api/public/v1/canonical-products')->assertOk();

        $response->assertJsonStructure([
            'data' => [
                ['id', 'canonical_key', 'display_name', 'manufacturer_brand', 'members_count', 'brands_count', 'min_price', 'max_price', 'avg_price', 'cheapest_brand'],
            ],
            'meta' => ['current_page', 'per_page', 'total', 'last_page'],
            'links' => ['first', 'last', 'next', 'prev'],
        ]);
        $this->assertSame(1, $response->json('meta.total'));
        $this->assertSame(2, $response->json('data.0.brands_count'));
        $this->assertSame(2, $response->json('data.0.members_count'));
        $this->assertEqualsWithDelta(1.0, (float) $response->json('data.0.min_price'), 0.001);
        $this->assertEqualsWithDelta(1.1, (float) $response->json('data.0.max_price'), 0.001);
        $this->assertSame('ab', $response->json('data.0.cheapest_brand.slug'));
    }

    public function test_default_min_brands_filter_hides_single_chain_canonicals(): void
    {
        // Multi-chain canonical -> kept.
        $this->seedCanonical('multi', 'Multi', ['ab' => 1.0, 'lidl' => 1.5]);
        // Single-chain canonical -> hidden by default.
        $this->seedCanonical('single', 'Single', ['masoutis' => 2.0]);

        $r = $this->getJson('/api/public/v1/canonical-products')->assertOk();
        $this->assertSame(1, $r->json('meta.total'));
        $this->assertSame('multi', $r->json('data.0.canonical_key'));

        // Override min_brands=1: both come back.
        $r2 = $this->getJson('/api/public/v1/canonical-products?min_brands=1')->assertOk();
        $this->assertSame(2, $r2->json('meta.total'));
    }

    public function test_q_filter_searches_display_name(): void
    {
        $this->seedCanonical('a', 'Lacta Γκοφρέτα 31g', ['ab' => 1.0, 'lidl' => 1.1]);
        $this->seedCanonical('b', 'Coca-Cola 1.5L', ['ab' => 1.5, 'lidl' => 1.6]);

        $r = $this->getJson('/api/public/v1/canonical-products?q='.urlencode('Lacta'))->assertOk();
        $this->assertSame(1, $r->json('meta.total'));
        $this->assertSame('a', $r->json('data.0.canonical_key'));
    }

    public function test_category_filter_is_case_insensitive(): void
    {
        $this->seedCanonical('a', 'A', ['ab' => 1.0, 'lidl' => 1.1], category: 'Σοκολάτες');
        $this->seedCanonical('b', 'B', ['ab' => 1.0, 'lidl' => 1.1], category: 'Ποτά');

        $r = $this->getJson('/api/public/v1/canonical-products?category='.urlencode('σοκολάτες'))
            ->assertOk();
        $this->assertSame(1, $r->json('meta.total'));
        $this->assertSame('a', $r->json('data.0.canonical_key'));
    }

    public function test_brand_filter_csv(): void
    {
        $this->seedCanonical('ab-lidl', 'A', ['ab' => 1.0, 'lidl' => 1.1]);
        $this->seedCanonical('masoutis-only', 'B', ['masoutis' => 2.0, 'sklavenitis' => 2.1]);

        $r = $this->getJson('/api/public/v1/canonical-products?brand=masoutis')
            ->assertOk();

        $this->assertSame(1, $r->json('meta.total'));
        $this->assertSame('masoutis-only', $r->json('data.0.canonical_key'));
    }

    public function test_sort_and_pagination(): void
    {
        $this->seedCanonical('a', 'A', ['ab' => 1.0, 'lidl' => 1.1]);                              // 2 brands
        $this->seedCanonical('b', 'B', ['ab' => 1.0, 'lidl' => 1.1, 'masoutis' => 1.2]);          // 3 brands
        $this->seedCanonical('c', 'C', ['ab' => 1.0, 'lidl' => 1.1, 'masoutis' => 1.2, 'mm' => 1.3]); // 4 brands

        // Default sort: brands_count desc.
        $r = $this->getJson('/api/public/v1/canonical-products')->assertOk();
        $this->assertSame(['c', 'b', 'a'], array_column($r->json('data'), 'canonical_key'));

        // Sort by display_name asc.
        $r2 = $this->getJson('/api/public/v1/canonical-products?sort=display_name&dir=asc')->assertOk();
        $this->assertSame(['A', 'B', 'C'], array_column($r2->json('data'), 'display_name'));

        // Pagination.
        $r3 = $this->getJson('/api/public/v1/canonical-products?per_page=2&page=1')->assertOk();
        $this->assertCount(2, $r3->json('data'));
        $this->assertSame(3, $r3->json('meta.total'));
        $this->assertSame(2, $r3->json('meta.last_page'));
    }

    public function test_unknown_query_params_are_rejected(): void
    {
        $this->getJson('/api/public/v1/canonical-products?bogus=1')
            ->assertUnprocessable()
            ->assertJsonValidationErrors(['bogus']);
    }

    public function test_per_page_above_max_is_rejected(): void
    {
        $this->getJson('/api/public/v1/canonical-products?per_page=101')
            ->assertUnprocessable()
            ->assertJsonValidationErrors(['per_page']);
    }

    public function test_internal_audit_fields_are_not_leaked(): void
    {
        $this->seedCanonical('a', 'A', ['ab' => 1.0, 'lidl' => 1.1]);

        $r = $this->getJson('/api/public/v1/canonical-products')->assertOk();
        $row = $r->json('data.0');

        $this->assertArrayNotHasKey('canonical_match_confidence', $row);
        $this->assertArrayNotHasKey('canonical_match_method', $row);
    }

    public function test_canonicals_with_no_offers_still_return_null_pricing(): void
    {
        // Two brands worth of members, but no offers — pricing fields null.
        $canonical = CanonicalProduct::create([
            'canonical_key' => 'noprice',
            'manufacturer_brand' => 'X',
            'display_name' => 'X',
            'category' => null,
        ]);
        $ab = $this->makeBrand(['slug' => 'ab']);
        $lidl = $this->makeBrand(['slug' => 'lidl', 'name' => 'Lidl', 'website_url' => 'https://lidl']);
        Product::create([
            'brand_id' => $ab->id,
            'name' => 'X1', 'normalized_name' => 'x1',
            'canonical_product_id' => $canonical->id,
        ]);
        Product::create([
            'brand_id' => $lidl->id,
            'name' => 'X2', 'normalized_name' => 'x2',
            'canonical_product_id' => $canonical->id,
        ]);
        $canonical->refreshAggregates();

        $r = $this->getJson('/api/public/v1/canonical-products')->assertOk();
        $this->assertSame(1, $r->json('meta.total'));
        $this->assertNull($r->json('data.0.min_price'));
        $this->assertNull($r->json('data.0.cheapest_brand'));
    }
}
