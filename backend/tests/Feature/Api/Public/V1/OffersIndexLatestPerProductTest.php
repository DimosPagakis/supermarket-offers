<?php

namespace Tests\Feature\Api\Public\V1;

use Illuminate\Support\Carbon;

class OffersIndexLatestPerProductTest extends PublicApiTestCase
{
    public function test_only_latest_offer_per_product_surfaces(): void
    {
        $brand = $this->makeBrand();
        $p = $this->makeProduct($brand, ['name' => 'feta', 'normalized_name' => 'feta']);

        $older = $this->makeOffer($p, [
            'price' => 6.00,
            'discount_pct' => 10,
            'scraped_at' => Carbon::now()->subDays(2),
        ]);
        $newer = $this->makeOffer($p, [
            'price' => 4.00,
            'discount_pct' => 33,
            'scraped_at' => Carbon::now()->subMinutes(1),
        ]);

        $response = $this->getJson('/api/public/v1/offers')->assertOk();

        $this->assertSame(1, $response->json('meta.total'));
        $this->assertSame($newer->id, $response->json('data.0.id'));
        $this->assertSame(4.0, (float) $response->json('data.0.price'));
    }

    public function test_latest_per_product_with_filter_still_chooses_among_matches(): void
    {
        // When a filter is active (e.g. has_discount=true), the latest-per-
        // product collapse is applied AFTER filtering — so we surface the
        // latest offer of those that match, not the absolute latest.
        //
        // Post-2026-05-25 the DB-level trigger refuses any row with no
        // promo signal at all; we test the filter by mixing a label-only
        // signal row (passes ingest, fails has_discount=true) against a
        // numeric-discount row (passes both).
        $brand = $this->makeBrand();
        $p = $this->makeProduct($brand, ['name' => 'feta', 'normalized_name' => 'feta']);

        $oldDiscounted = $this->makeOffer($p, [
            'price' => 4.00,
            'original_price' => 6.00,
            'discount_pct' => 33,
            'scraped_at' => Carbon::now()->subDays(2),
        ]);
        // Newer offer with a label-only signal: ingest accepts it,
        // ``has_discount=true`` rejects it (discount_pct is null).
        $newerLabelOnly = $this->makeOffer($p, [
            'price' => 6.00,
            'original_price' => null,
            'discount_pct' => null,
            'promo_label' => '1+1 δώρο',
            'promo_type' => 'bxgy_free',
            'scraped_at' => Carbon::now()->subMinutes(1),
        ]);

        $response = $this->getJson('/api/public/v1/offers?has_discount=true')->assertOk();

        $this->assertSame(1, $response->json('meta.total'));
        $this->assertSame($oldDiscounted->id, $response->json('data.0.id'));
    }
}
