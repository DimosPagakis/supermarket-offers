<?php

namespace Tests\Feature\Api;

use App\Models\Brand;
use App\Models\CrawlRun;

class CrawlRunStartTest extends ApiTestCase
{
    public function test_unauthenticated_requests_are_rejected(): void
    {
        $this->postJson('/api/v1/crawl-runs', [])->assertUnauthorized();
    }

    public function test_creates_a_running_crawl_run(): void
    {
        $this->authedAsCrawler();
        $brand = Brand::create([
            'name' => 'Test Brand',
            'slug' => 'test',
            'website_url' => 'https://example.com',
        ]);

        $response = $this->postJson('/api/v1/crawl-runs', [
            'brand_id' => $brand->id,
            'triggered_by' => 'manual',
        ])->assertCreated();

        $response->assertJsonPath('data.brand_id', $brand->id);
        $response->assertJsonPath('data.status', CrawlRun::STATUS_RUNNING);
        $response->assertJsonPath('data.triggered_by', 'manual');
        $this->assertNotNull($response->json('data.started_at'));
        $this->assertNull($response->json('data.finished_at'));

        $this->assertDatabaseHas('crawl_runs', [
            'brand_id' => $brand->id,
            'status' => CrawlRun::STATUS_RUNNING,
            'triggered_by' => 'manual',
        ]);
    }

    public function test_validates_brand_existence(): void
    {
        $this->authedAsCrawler();

        $this->postJson('/api/v1/crawl-runs', [
            'brand_id' => 99999,
            'triggered_by' => 'schedule',
        ])->assertUnprocessable()->assertJsonValidationErrors('brand_id');
    }

    public function test_validates_triggered_by(): void
    {
        $this->authedAsCrawler();
        $brand = Brand::create([
            'name' => 'B', 'slug' => 'b', 'website_url' => 'https://b.gr',
        ]);

        $this->postJson('/api/v1/crawl-runs', [
            'brand_id' => $brand->id,
            'triggered_by' => 'cosmic-ray',
        ])->assertUnprocessable()->assertJsonValidationErrors('triggered_by');
    }

    public function test_inactive_brand_is_rejected(): void
    {
        $this->authedAsCrawler();
        $brand = Brand::create([
            'name' => 'Paused Chain',
            'slug' => 'paused',
            'website_url' => 'https://paused.gr',
            'active' => false,
        ]);

        $this->postJson('/api/v1/crawl-runs', [
            'brand_id' => $brand->id,
            'triggered_by' => 'schedule',
        ])->assertUnprocessable()->assertJsonValidationErrors('brand_id');

        $this->assertDatabaseMissing('crawl_runs', ['brand_id' => $brand->id]);
    }
}
