<?php

namespace Tests\Feature\Api\Public\V1;

use Database\Seeders\BrandSeeder;

class BrandIndexPublicTest extends PublicApiTestCase
{
    public function test_no_auth_required(): void
    {
        $this->seed(BrandSeeder::class);

        $response = $this->getJson('/api/public/v1/brands')->assertOk();

        // 4 of 5 seeded brands are active. Sklavenitis is seeded inactive
        // (2026-05-25) — its only entry point ships the chain catalogue
        // not a flyer. See BrandSeeder.
        $response->assertJsonCount(4, 'data');
    }

    public function test_only_active_brands_are_returned(): void
    {
        $this->seed(BrandSeeder::class);
        \App\Models\Brand::query()->where('slug', 'lidl')->update(['active' => false]);

        $response = $this->getJson('/api/public/v1/brands')->assertOk();

        // 5 seeded - 1 inactive (sklavenitis) - 1 we just flipped (lidl) = 3.
        $response->assertJsonCount(3, 'data');
        $slugs = array_column($response->json('data'), 'slug');
        $this->assertNotContains('lidl', $slugs);
        $this->assertNotContains('sklavenitis', $slugs);
    }

    public function test_response_omits_internal_crawl_config(): void
    {
        $this->seed(BrandSeeder::class);

        $response = $this->getJson('/api/public/v1/brands')->assertOk();

        $first = $response->json('data.0');
        $this->assertArrayHasKey('slug', $first);
        $this->assertArrayHasKey('website_url', $first);
        $this->assertArrayHasKey('country_code', $first);
        $this->assertArrayNotHasKey('crawl_config', $first, 'Public brand response must not leak crawl_config.');
        $this->assertArrayNotHasKey('active', $first, 'Public brand response must not leak the internal active flag.');
    }
}
