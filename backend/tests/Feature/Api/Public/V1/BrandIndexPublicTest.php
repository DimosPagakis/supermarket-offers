<?php

namespace Tests\Feature\Api\Public\V1;

use Database\Seeders\BrandSeeder;

class BrandIndexPublicTest extends PublicApiTestCase
{
    public function test_no_auth_required(): void
    {
        $this->seed(BrandSeeder::class);

        $response = $this->getJson('/api/public/v1/brands')->assertOk();

        $response->assertJsonCount(5, 'data');
    }

    public function test_only_active_brands_are_returned(): void
    {
        $this->seed(BrandSeeder::class);
        \App\Models\Brand::query()->where('slug', 'lidl')->update(['active' => false]);

        $response = $this->getJson('/api/public/v1/brands')->assertOk();

        $response->assertJsonCount(4, 'data');
        $slugs = array_column($response->json('data'), 'slug');
        $this->assertNotContains('lidl', $slugs);
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
