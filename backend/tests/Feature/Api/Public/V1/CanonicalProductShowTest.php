<?php

namespace Tests\Feature\Api\Public\V1;

use App\Models\CanonicalProduct;
use Illuminate\Support\Carbon;

class CanonicalProductShowTest extends PublicApiTestCase
{
    public function test_show_returns_comparison_view_with_one_offer_per_member(): void
    {
        $canonical = CanonicalProduct::create([
            'canonical_key' => 'lacta:gofreta:31g:1',
            'manufacturer_brand' => 'Lacta',
            'display_name' => 'Lacta Γκοφρέτα 31g',
            'category' => 'Σοκολάτες',
            'size_value' => 31.0,
            'size_unit' => 'g',
            'pack_count' => 1,
        ]);

        $ab = $this->makeBrand(['slug' => 'ab', 'name' => 'AB']);
        $lidl = $this->makeBrand(['slug' => 'lidl', 'name' => 'Lidl', 'website_url' => 'https://lidl']);
        $p1 = $this->makeProduct($ab, [
            'name' => 'Lacta @ AB',
            'normalized_name' => 'lacta @ ab',
            'canonical_product_id' => $canonical->id,
        ]);
        $p2 = $this->makeProduct($lidl, [
            'name' => 'Lacta @ Lidl',
            'normalized_name' => 'lacta @ lidl',
            'canonical_product_id' => $canonical->id,
        ]);

        // p1 has two offers — only the latest should surface.
        $this->makeOffer($p1, ['price' => 1.50, 'scraped_at' => Carbon::now()->subDays(2)]);
        $this->makeOffer($p1, ['price' => 1.20, 'scraped_at' => Carbon::now()]);
        // p2 has one offer.
        $this->makeOffer($p2, ['price' => 1.10]);

        $canonical->refreshAggregates();

        $response = $this->getJson("/api/public/v1/canonical-products/{$canonical->id}")
            ->assertOk();

        $response->assertJsonStructure([
            'data' => [
                'id', 'canonical_key', 'display_name', 'manufacturer_brand',
                'members_count', 'brands_count',
                'offers' => [
                    ['brand' => ['slug'], 'product' => ['id'], 'offer' => ['price']],
                ],
                'min_price', 'max_price', 'avg_price', 'price_savings',
            ],
        ]);

        // 2 members -> 2 offers.
        $this->assertCount(2, $response->json('data.offers'));
        // Sorted cheapest first.
        $this->assertSame(1.1, $response->json('data.offers.0.offer.price'));
        $this->assertSame('lidl', $response->json('data.offers.0.brand.slug'));
        $this->assertSame(1.2, $response->json('data.offers.1.offer.price'));
        $this->assertSame('ab', $response->json('data.offers.1.brand.slug'));

        $this->assertSame(1.1, $response->json('data.min_price'));
        $this->assertSame(1.2, $response->json('data.max_price'));
        $this->assertEqualsWithDelta(1.15, $response->json('data.avg_price'), 0.01);
        $this->assertEqualsWithDelta(0.10, $response->json('data.price_savings'), 0.01);
    }

    public function test_show_returns_404_for_unknown_id(): void
    {
        $this->getJson('/api/public/v1/canonical-products/999999')->assertNotFound();
    }

    public function test_show_filters_out_expired_offers(): void
    {
        $canonical = CanonicalProduct::create([
            'canonical_key' => 'x',
            'manufacturer_brand' => 'X',
            'display_name' => 'X',
        ]);
        $ab = $this->makeBrand(['slug' => 'ab']);
        $p = $this->makeProduct($ab, [
            'name' => 'X', 'normalized_name' => 'x',
            'canonical_product_id' => $canonical->id,
        ]);
        $this->makeOffer($p, [
            'price' => 1.0,
            'valid_from' => '2020-01-01',
            'valid_to' => '2020-12-31',
        ]);
        $canonical->refreshAggregates();

        $r = $this->getJson("/api/public/v1/canonical-products/{$canonical->id}")
            ->assertOk();
        $this->assertCount(0, $r->json('data.offers'));
        $this->assertNull($r->json('data.min_price'));
    }

    public function test_show_does_not_leak_internal_audit_fields(): void
    {
        $canonical = CanonicalProduct::create([
            'canonical_key' => 'x',
            'manufacturer_brand' => 'X',
            'display_name' => 'X',
        ]);
        $ab = $this->makeBrand(['slug' => 'ab']);
        $p = $this->makeProduct($ab, [
            'name' => 'X', 'normalized_name' => 'x',
            'canonical_product_id' => $canonical->id,
            'canonical_match_confidence' => 0.97,
            'canonical_match_method' => 'rule',
        ]);
        $this->makeOffer($p, ['price' => 1.0]);
        $canonical->refreshAggregates();

        $r = $this->getJson("/api/public/v1/canonical-products/{$canonical->id}")
            ->assertOk();
        $row = $r->json('data');
        $this->assertArrayNotHasKey('canonical_match_confidence', $row);
        $this->assertArrayNotHasKey('canonical_match_method', $row);
        $product = $r->json('data.offers.0.product');
        $this->assertArrayNotHasKey('canonical_match_confidence', $product);
        $this->assertArrayNotHasKey('canonical_match_method', $product);
    }
}
