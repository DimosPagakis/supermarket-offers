<?php

namespace Tests\Feature\Api;

use App\Models\Brand;
use App\Models\CrawlRun;
use App\Models\Offer;
use App\Models\Product;

class CrawlRunPatchTest extends ApiTestCase
{
    private function makeRun(): CrawlRun
    {
        $brand = Brand::create([
            'name' => 'AB', 'slug' => 'ab', 'website_url' => 'https://www.ab.gr',
        ]);

        return CrawlRun::create([
            'brand_id' => $brand->id,
            'started_at' => now(),
            'status' => CrawlRun::STATUS_RUNNING,
            'triggered_by' => 'manual',
        ]);
    }

    public function test_unauthenticated_requests_are_rejected(): void
    {
        $run = $this->makeRun();
        $this->patchJson("/api/v1/crawl-runs/{$run->id}", [])->assertUnauthorized();
    }

    public function test_marking_run_success_sets_finished_at(): void
    {
        $this->authedAsCrawler();
        $run = $this->makeRun();

        $response = $this->patchJson("/api/v1/crawl-runs/{$run->id}", [
            'status' => 'success',
            'offers_found' => 42,
            'offers_persisted' => 40,
        ])->assertOk();

        $response->assertJsonPath('data.status', 'success');
        $response->assertJsonPath('data.offers_found', 42);
        $response->assertJsonPath('data.offers_persisted', 40);
        $this->assertNotNull($response->json('data.finished_at'));

        $run->refresh();
        $this->assertNotNull($run->finished_at);
        $this->assertSame(CrawlRun::STATUS_SUCCESS, $run->status);
    }

    public function test_failed_status_stores_error_message(): void
    {
        $this->authedAsCrawler();
        $run = $this->makeRun();

        $this->patchJson("/api/v1/crawl-runs/{$run->id}", [
            'status' => 'failed',
            'offers_found' => 0,
            'error_message' => 'sklavenitis returned 403',
        ])->assertOk()
          ->assertJsonPath('data.status', 'failed')
          ->assertJsonPath('data.error_message', 'sklavenitis returned 403');
    }

    public function test_offers_persisted_is_auto_derived_when_omitted(): void
    {
        $this->authedAsCrawler();
        $run = $this->makeRun();

        $product = Product::create([
            'brand_id' => $run->brand_id,
            'external_id' => 'X',
            'name' => 'X',
            'normalized_name' => 'x',
        ]);
        Offer::create([
            'product_id' => $product->id,
            'crawl_run_id' => $run->id,
            'price' => 1.00,
            'currency' => 'EUR',
            'scraped_at' => now(),
        ]);
        Offer::create([
            'product_id' => $product->id,
            'crawl_run_id' => $run->id,
            'price' => 2.00,
            'currency' => 'EUR',
            'scraped_at' => now(),
        ]);

        $response = $this->patchJson("/api/v1/crawl-runs/{$run->id}", [
            'status' => 'success',
            'offers_found' => 2,
        ])->assertOk();

        $response->assertJsonPath('data.offers_persisted', 2);
    }

    public function test_validates_status(): void
    {
        $this->authedAsCrawler();
        $run = $this->makeRun();

        $this->patchJson("/api/v1/crawl-runs/{$run->id}", [
            'status' => 'banana',
            'offers_found' => 1,
        ])->assertUnprocessable()->assertJsonValidationErrors('status');
    }

    public function test_terminal_run_cannot_be_patched_again(): void
    {
        $this->authedAsCrawler();
        $run = $this->makeRun();
        $run->update([
            'status' => CrawlRun::STATUS_SUCCESS,
            'finished_at' => now(),
            'offers_found' => 5,
            'offers_persisted' => 5,
        ]);

        $this->patchJson("/api/v1/crawl-runs/{$run->id}", [
            'status' => 'failed',
            'offers_found' => 0,
            'error_message' => 'trying to flip a closed run',
        ])->assertUnprocessable()->assertJsonValidationErrors('run');

        $run->refresh();
        $this->assertSame(CrawlRun::STATUS_SUCCESS, $run->status);
        $this->assertSame(5, $run->offers_found);
    }

    public function test_persisted_exceeding_found_is_rejected(): void
    {
        $this->authedAsCrawler();
        $run = $this->makeRun();

        $this->patchJson("/api/v1/crawl-runs/{$run->id}", [
            'status' => 'success',
            'offers_found' => 10,
            'offers_persisted' => 11,
        ])->assertUnprocessable()->assertJsonValidationErrors('offers_persisted');

        $run->refresh();
        $this->assertSame(CrawlRun::STATUS_RUNNING, $run->status);
    }
}
