<?php

namespace Tests\Feature\Api;

use App\Models\Brand;
use App\Models\CrawlRun;
use App\Models\Offer;
use App\Models\Product;
use App\Services\ProductResolver;
use RuntimeException;

class CrawlRunOffersTest extends ApiTestCase
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
        $this->postJson('/api/v1/crawl-runs/1/offers', [])->assertUnauthorized();
    }

    public function test_happy_path_creates_products_and_offers(): void
    {
        $this->authedAsCrawler();
        $run = $this->makeRun();

        $response = $this->postJson("/api/v1/crawl-runs/{$run->id}/offers", [
            'offers' => [
                [
                    'external_id' => 'SKU-1',
                    'name' => 'Φέτα ΠΟΠ 400γρ',
                    'url' => 'https://www.ab.gr/p/1',
                    'image_url' => 'https://cdn.ab.gr/1.jpg',
                    'category' => 'Τυριά',
                    'unit' => 'pcs',
                    'price' => 4.99,
                    'original_price' => 6.49,
                    'discount_pct' => 23,
                    'currency' => 'EUR',
                    'valid_from' => '2026-05-25',
                    'valid_to' => '2026-05-31',
                    'scraped_at' => '2026-05-25T08:00:00Z',
                ],
                [
                    'external_id' => null,
                    'name' => 'Γάλα Φρέσκο 1λ',
                    'price' => 1.49,
                    'currency' => 'EUR',
                    'scraped_at' => '2026-05-25T08:00:00Z',
                ],
            ],
        ])->assertCreated();

        $response->assertJsonPath('data.persisted', 2);
        $response->assertJsonPath('data.products_created', 2);
        $response->assertJsonPath('data.products_updated', 0);

        $this->assertSame(2, Product::query()->where('brand_id', $run->brand_id)->count());
        $this->assertSame(2, Offer::query()->where('crawl_run_id', $run->id)->count());

        $product = Product::query()->where('external_id', 'SKU-1')->first();
        $this->assertNotNull($product);
        $this->assertSame('Φέτα ΠΟΠ 400γρ', $product->name);
        $this->assertNotEmpty($product->normalized_name);
    }

    public function test_second_push_is_idempotent_for_product_matching(): void
    {
        $this->authedAsCrawler();
        $run1 = $this->makeRun();
        $brandId = $run1->brand_id;

        $body = [
            'offers' => [
                [
                    'external_id' => 'SKU-42',
                    'name' => 'Καφές Αλεσμένος 250γρ',
                    'price' => 3.20,
                    'currency' => 'EUR',
                    'scraped_at' => '2026-05-25T08:00:00Z',
                ],
                [
                    // no external_id — match by normalized_name
                    'external_id' => null,
                    'name' => 'Ψωμί Ολικής 500γρ',
                    'price' => 1.10,
                    'currency' => 'EUR',
                    'scraped_at' => '2026-05-25T08:00:00Z',
                ],
            ],
        ];

        $this->postJson("/api/v1/crawl-runs/{$run1->id}/offers", $body)->assertCreated();
        $this->assertSame(2, Product::query()->where('brand_id', $brandId)->count());

        // Simulate a second run for same brand pushing the same items.
        $run2 = CrawlRun::create([
            'brand_id' => $brandId,
            'started_at' => now(),
            'status' => CrawlRun::STATUS_RUNNING,
            'triggered_by' => 'schedule',
        ]);

        $resp = $this->postJson("/api/v1/crawl-runs/{$run2->id}/offers", $body)->assertCreated();
        $resp->assertJsonPath('data.products_created', 0);

        // No new products, but two more offer rows attached to the new run.
        $this->assertSame(2, Product::query()->where('brand_id', $brandId)->count());
        $this->assertSame(2, Offer::query()->where('crawl_run_id', $run2->id)->count());
    }

    public function test_validation_rejects_bad_payload(): void
    {
        $this->authedAsCrawler();
        $run = $this->makeRun();

        $this->postJson("/api/v1/crawl-runs/{$run->id}/offers", [
            'offers' => [
                [
                    'name' => '',
                    'price' => -1,
                    'discount_pct' => 250,
                    'currency' => 'EURO',
                    'scraped_at' => 'not-a-date',
                ],
            ],
        ])->assertUnprocessable()->assertJsonValidationErrors([
            'offers.0.name',
            'offers.0.price',
            'offers.0.discount_pct',
            'offers.0.currency',
            'offers.0.scraped_at',
        ]);
    }

    public function test_empty_offers_array_is_rejected(): void
    {
        $this->authedAsCrawler();
        $run = $this->makeRun();

        $this->postJson("/api/v1/crawl-runs/{$run->id}/offers", [
            'offers' => [],
        ])->assertUnprocessable()->assertJsonValidationErrors('offers');
    }

    public function test_pushing_to_finished_run_is_rejected(): void
    {
        $this->authedAsCrawler();
        $run = $this->makeRun();
        $run->update([
            'status' => CrawlRun::STATUS_SUCCESS,
            'finished_at' => now(),
        ]);

        $this->postJson("/api/v1/crawl-runs/{$run->id}/offers", [
            'offers' => [
                [
                    'name' => 'Late Arrival',
                    'price' => 1.00,
                    'currency' => 'EUR',
                    'scraped_at' => '2026-05-25T08:00:00Z',
                ],
            ],
        ])->assertUnprocessable()->assertJsonValidationErrors('run');

        $this->assertSame(0, Offer::query()->where('crawl_run_id', $run->id)->count());
    }

    public function test_invalid_date_range_is_rejected(): void
    {
        $this->authedAsCrawler();
        $run = $this->makeRun();

        $this->postJson("/api/v1/crawl-runs/{$run->id}/offers", [
            'offers' => [
                [
                    'name' => 'Time Traveller',
                    'price' => 1.00,
                    'currency' => 'EUR',
                    'valid_from' => '2026-06-10',
                    'valid_to' => '2026-06-01',
                    'scraped_at' => '2026-05-25T08:00:00Z',
                ],
            ],
        ])->assertUnprocessable()->assertJsonValidationErrors('offers.0.valid_to');
    }

    public function test_promo_label_and_type_round_trip_through_public_api(): void
    {
        // POST an AB-style "1+1 δώρο" offer and assert that both the new
        // promo_label / promo_type fields persist and surface on the
        // public read endpoint exactly as sent.
        $this->authedAsCrawler();
        $run = $this->makeRun();

        $this->postJson("/api/v1/crawl-runs/{$run->id}/offers", [
            'offers' => [
                [
                    'external_id' => 'AB-7798261',
                    'name' => 'Στεγνά Πανάκια Πατώματος 10 Refills',
                    'price' => 5.25,
                    'original_price' => null,
                    'discount_pct' => null,
                    'promo_label' => '1+1 δώρο',
                    'promo_type' => 'bxgy_free',
                    'currency' => 'EUR',
                    'scraped_at' => '2026-05-25T08:00:00Z',
                ],
            ],
        ])->assertCreated();

        $offer = Offer::query()->where('crawl_run_id', $run->id)->firstOrFail();
        $this->assertSame('1+1 δώρο', $offer->promo_label);
        $this->assertSame('bxgy_free', $offer->promo_type);
        $this->assertNull($offer->original_price);
        $this->assertNull($offer->discount_pct);

        // The public-read side must also expose the new fields verbatim
        // so frontend / third-party consumers can render the badge.
        $resp = $this->getJson("/api/public/v1/offers/{$offer->id}")->assertOk();
        $resp->assertJsonPath('data.promo_label', '1+1 δώρο');
        $resp->assertJsonPath('data.promo_type', 'bxgy_free');
        $resp->assertJsonPath('data.original_price', null);
        $resp->assertJsonPath('data.discount_pct', null);
    }

    public function test_unknown_promo_type_value_is_rejected(): void
    {
        // promo_type is an enum (see Offer::PROMO_TYPES). Anything else
        // must trip the FormRequest's Rule::in() so a crawler bug surfaces
        // immediately instead of silently corrupting the column.
        $this->authedAsCrawler();
        $run = $this->makeRun();

        $this->postJson("/api/v1/crawl-runs/{$run->id}/offers", [
            'offers' => [
                [
                    'name' => 'Something',
                    'price' => 1.00,
                    'promo_label' => 'foo',
                    'promo_type' => 'mystery_meat',
                    'currency' => 'EUR',
                    'scraped_at' => '2026-05-25T08:00:00Z',
                ],
            ],
        ])->assertUnprocessable()->assertJsonValidationErrors('offers.0.promo_type');

        $this->assertSame(0, Offer::query()->where('crawl_run_id', $run->id)->count());
    }

    public function test_omitting_promo_fields_remains_valid_for_back_compat(): void
    {
        // Pre-promo-label clients send no promo_label / promo_type at all.
        // Their payloads must still validate and persist as null.
        $this->authedAsCrawler();
        $run = $this->makeRun();

        $this->postJson("/api/v1/crawl-runs/{$run->id}/offers", [
            'offers' => [
                [
                    'name' => 'Legacy Client Item',
                    'price' => 2.50,
                    'currency' => 'EUR',
                    'scraped_at' => '2026-05-25T08:00:00Z',
                ],
            ],
        ])->assertCreated();

        $offer = Offer::query()->where('crawl_run_id', $run->id)->firstOrFail();
        $this->assertNull($offer->promo_label);
        $this->assertNull($offer->promo_type);
    }

    public function test_transaction_rolls_back_on_resolver_exception(): void
    {
        $this->authedAsCrawler();
        $run = $this->makeRun();

        // Swap the resolver for one that explodes on the second item, so we
        // can prove (a) the response is a structured 500 and (b) nothing
        // from the batch — not even the first item — gets persisted.
        $this->mock(ProductResolver::class, function ($mock) {
            $mock->shouldReceive('resolve')
                ->once()
                ->andReturn([
                    'product' => Product::create([
                        'brand_id' => 1,
                        'external_id' => 'OK',
                        'name' => 'First',
                        'normalized_name' => 'first',
                    ]),
                    'created' => true,
                    'updated' => false,
                ]);
            $mock->shouldReceive('resolve')
                ->once()
                ->andThrow(new RuntimeException('boom'));
        });

        $response = $this->postJson("/api/v1/crawl-runs/{$run->id}/offers", [
            'offers' => [
                [
                    'name' => 'First',
                    'price' => 1.00,
                    'currency' => 'EUR',
                    'scraped_at' => '2026-05-25T08:00:00Z',
                ],
                [
                    'name' => 'Second',
                    'price' => 2.00,
                    'currency' => 'EUR',
                    'scraped_at' => '2026-05-25T08:00:00Z',
                ],
            ],
        ])->assertStatus(500);

        $response->assertJsonPath('error', 'offer_push_failed');
        $this->assertStringContainsString('Safe to retry', $response->json('message'));

        // No offers should have made it into the DB — full rollback.
        $this->assertSame(0, Offer::query()->where('crawl_run_id', $run->id)->count());
        // The first-item Product created inside the mocked resolver call
        // happens outside the controller's transaction (the mock instantiates
        // it eagerly), so we don't assert on Product counts here — only on
        // the controller-managed Offer rows.
    }
}
