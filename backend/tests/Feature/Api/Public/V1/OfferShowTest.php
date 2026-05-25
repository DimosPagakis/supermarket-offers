<?php

namespace Tests\Feature\Api\Public\V1;

use Illuminate\Support\Carbon;

class OfferShowTest extends PublicApiTestCase
{
    public function test_happy_path(): void
    {
        $brand = $this->makeBrand();
        $product = $this->makeProduct($brand, ['name' => 'feta', 'normalized_name' => 'feta']);
        $offer = $this->makeOffer($product);

        $response = $this->getJson("/api/public/v1/offers/{$offer->id}")->assertOk();

        $response->assertJsonPath('data.id', $offer->id);
        $response->assertJsonPath('data.product.name', 'feta');
        $response->assertJsonPath('data.brand.slug', 'ab');
        // History should NOT be present without ?include_history.
        $this->assertArrayNotHasKey('history', $response->json('data'));
    }

    public function test_show_404_for_unknown_id(): void
    {
        $this->getJson('/api/public/v1/offers/999999')->assertNotFound();
    }

    public function test_include_history_returns_chronological_history(): void
    {
        $brand = $this->makeBrand();
        $product = $this->makeProduct($brand, ['name' => 'feta', 'normalized_name' => 'feta']);
        $older = $this->makeOffer($product, ['price' => 6.00, 'scraped_at' => Carbon::now()->subDays(3)]);
        $middle = $this->makeOffer($product, ['price' => 5.00, 'scraped_at' => Carbon::now()->subDays(2)]);
        $newest = $this->makeOffer($product, ['price' => 4.00, 'scraped_at' => Carbon::now()->subHours(1)]);

        $response = $this->getJson("/api/public/v1/offers/{$newest->id}?include_history=true")->assertOk();

        $history = $response->json('data.history');
        $this->assertCount(3, $history);
        // Ordered scraped_at desc.
        $this->assertSame($newest->id, $history[0]['id']);
        $this->assertSame($middle->id, $history[1]['id']);
        $this->assertSame($older->id, $history[2]['id']);
    }
}
