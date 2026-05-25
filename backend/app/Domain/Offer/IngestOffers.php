<?php

namespace App\Domain\Offer;

use App\Models\CrawlRun;
use App\Models\Offer;
use App\Services\ProductResolver;
use Illuminate\Support\Facades\DB;

/**
 * Persist a batch of scraped offers against a crawl run.
 *
 *   1. Resolves a Product per offer via {@see ProductResolver} —
 *      either an existing row (matched by brand_id + external_id, or
 *      brand_id + normalized_name) gets refreshed, or a new one is
 *      created. The resolver reports which branch it took so the
 *      action can keep the `products_created` / `products_updated`
 *      counts.
 *   2. Creates one `offers` row per item linked to both the resolved
 *      product and the supplied crawl run.
 *
 * Runs inside a single `DB::transaction` — any exception rolls the
 * whole batch back so the crawler can safely retry the same payload
 * (product matching is idempotent on brand_id + external_id /
 * normalized_name). This action does NOT mutate the run's status;
 * the crawler owns lifecycle transitions via PATCH /crawl-runs/{run}.
 * The HTTP envelope (200/500, error JSON) is the caller's concern;
 * this action only signals failure by letting the exception
 * propagate.
 */
class IngestOffers
{
    public function __construct(private readonly ProductResolver $resolver) {}

    /**
     * @param  array<int, array<string, mixed>>  $offers  validated payload
     */
    public function __invoke(CrawlRun $run, array $offers): IngestResult
    {
        $brandId = (int) $run->brand_id;

        $persisted = 0;
        $created = 0;
        $updated = 0;

        DB::transaction(function () use ($offers, $run, $brandId, &$persisted, &$created, &$updated): void {
            foreach ($offers as $item) {
                $result = $this->resolver->resolve($brandId, $item);

                if ($result['created']) {
                    $created++;
                } elseif ($result['updated']) {
                    $updated++;
                }

                Offer::create([
                    'product_id' => $result['product']->id,
                    'crawl_run_id' => $run->id,
                    'price' => $item['price'],
                    'original_price' => $item['original_price'] ?? null,
                    'discount_pct' => $item['discount_pct'] ?? null,
                    'currency' => $item['currency'] ?? 'EUR',
                    'valid_from' => $item['valid_from'] ?? null,
                    'valid_to' => $item['valid_to'] ?? null,
                    'scraped_at' => $item['scraped_at'],
                ]);

                $persisted++;
            }
        });

        return new IngestResult(
            persisted: $persisted,
            productsCreated: $created,
            productsUpdated: $updated,
        );
    }
}
