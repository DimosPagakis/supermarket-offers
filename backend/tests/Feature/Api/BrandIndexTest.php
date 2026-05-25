<?php

namespace Tests\Feature\Api;

use Database\Seeders\BrandSeeder;

class BrandIndexTest extends ApiTestCase
{
    public function test_unauthenticated_requests_are_rejected(): void
    {
        $this->getJson('/api/v1/brands')->assertUnauthorized();
    }

    public function test_returns_seeded_brands_with_crawl_config(): void
    {
        $this->seed(BrandSeeder::class);
        $this->authedAsCrawler();

        $response = $this->getJson('/api/v1/brands')->assertOk();

        $response->assertJsonCount(5, 'data');

        $first = $response->json('data.0');
        $this->assertArrayHasKey('id', $first);
        $this->assertArrayHasKey('slug', $first);
        $this->assertArrayHasKey('crawl_config', $first);
        $this->assertIsArray($first['crawl_config']);
        $this->assertArrayHasKey('start_url', $first['crawl_config']);
        $this->assertArrayHasKey('strategy', $first['crawl_config']);
        $this->assertArrayHasKey('rate_limit_ms', $first['crawl_config']);
        $this->assertArrayHasKey('respect_robots_txt', $first['crawl_config']);
        $this->assertArrayHasKey('cache_ttl_seconds', $first['crawl_config']);
    }

    public function test_inactive_brands_are_excluded(): void
    {
        $this->seed(BrandSeeder::class);
        \App\Models\Brand::query()->where('slug', 'lidl')->update(['active' => false]);

        $this->authedAsCrawler();

        $response = $this->getJson('/api/v1/brands')->assertOk();
        $response->assertJsonCount(4, 'data');
        $slugs = array_column($response->json('data'), 'slug');
        $this->assertNotContains('lidl', $slugs);
    }
}
