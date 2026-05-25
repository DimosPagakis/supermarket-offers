<?php

namespace Tests\Unit\Domain\Offer;

use App\Domain\Offer\IngestOffers;
use App\Domain\Offer\IngestResult;
use App\Models\Brand;
use App\Models\CrawlRun;
use App\Models\Offer;
use App\Models\Product;
use App\Services\ProductResolver;
use Illuminate\Foundation\Testing\RefreshDatabase;
use RuntimeException;
use Tests\TestCase;

/**
 * Exercises the IngestOffers action directly — without an HTTP round
 * trip — to prove it is independently usable by future callers
 * (artisan replay, scheduled re-rank, event handlers). The existing
 * feature tests under tests/Feature/Api/CrawlRunOffersTest.php cover
 * the same logic at the HTTP boundary; these tests are the smaller
 * seam for callers that aren't a controller.
 */
class IngestOffersTest extends TestCase
{
    use RefreshDatabase;

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

    public function test_happy_path_persists_offers_and_returns_counts(): void
    {
        $run = $this->makeRun();
        $action = app(IngestOffers::class);

        $result = $action($run, [
            [
                'external_id' => 'SKU-1',
                'name' => 'Φέτα ΠΟΠ 400γρ',
                'price' => 4.99,
                'currency' => 'EUR',
                'scraped_at' => '2026-05-25T08:00:00Z',
            ],
            [
                'external_id' => 'SKU-2',
                'name' => 'Γάλα 1λ',
                'price' => 1.49,
                'currency' => 'EUR',
                'scraped_at' => '2026-05-25T08:00:00Z',
            ],
        ]);

        $this->assertInstanceOf(IngestResult::class, $result);
        $this->assertSame(2, $result->persisted);
        $this->assertSame(2, $result->productsCreated);
        $this->assertSame(0, $result->productsUpdated);

        $this->assertSame(2, Product::query()->where('brand_id', $run->brand_id)->count());
        $this->assertSame(2, Offer::query()->where('crawl_run_id', $run->id)->count());
    }

    public function test_resolver_creates_first_then_updates_on_second_call(): void
    {
        $run = $this->makeRun();
        $action = app(IngestOffers::class);

        $first = $action($run, [
            [
                'external_id' => 'SKU-7',
                'name' => 'Καφές 250γρ',
                'price' => 3.20,
                'currency' => 'EUR',
                'scraped_at' => '2026-05-25T08:00:00Z',
            ],
        ]);

        $this->assertSame(1, $first->productsCreated);
        $this->assertSame(0, $first->productsUpdated);

        // Second invocation: same external_id, mutable attribute changed
        // (category). The resolver should match the existing product and
        // refresh it — productsUpdated must tick.
        $second = $action($run, [
            [
                'external_id' => 'SKU-7',
                'name' => 'Καφές 250γρ',
                'category' => 'Ροφήματα',
                'price' => 2.99,
                'currency' => 'EUR',
                'scraped_at' => '2026-05-25T09:00:00Z',
            ],
        ]);

        $this->assertSame(0, $second->productsCreated);
        $this->assertSame(1, $second->productsUpdated);

        // Still a single product row, two offer rows.
        $this->assertSame(1, Product::query()->where('brand_id', $run->brand_id)->count());
        $this->assertSame(2, Offer::query()->where('crawl_run_id', $run->id)->count());
    }

    public function test_throwing_resolver_rolls_back_and_propagates(): void
    {
        $run = $this->makeRun();

        // Swap the container's resolver for one that creates a product
        // on the first call (so we can assert rollback wiped it) and
        // throws on the second.
        $this->mock(ProductResolver::class, function ($mock) use ($run) {
            $mock->shouldReceive('resolve')
                ->once()
                ->andReturnUsing(fn () => [
                    'product' => Product::create([
                        'brand_id' => $run->brand_id,
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

        $action = app(IngestOffers::class);

        $threw = false;
        try {
            $action($run, [
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
            ]);
        } catch (RuntimeException $e) {
            $threw = true;
            $this->assertSame('boom', $e->getMessage());
        }

        $this->assertTrue($threw, 'IngestOffers must re-raise so the controller envelope catches it.');

        // Full rollback: no offer rows, and the product that the first
        // resolve() inserted inside the transaction is gone too.
        $this->assertSame(0, Offer::query()->where('crawl_run_id', $run->id)->count());
        $this->assertSame(0, Product::query()->where('brand_id', $run->brand_id)->where('external_id', 'OK')->count());
    }

    public function test_result_to_array_matches_wire_shape(): void
    {
        $result = new IngestResult(persisted: 3, productsCreated: 2, productsUpdated: 1);

        $this->assertSame([
            'persisted' => 3,
            'products_created' => 2,
            'products_updated' => 1,
        ], $result->toArray());
    }
}
