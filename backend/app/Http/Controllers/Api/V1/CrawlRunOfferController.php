<?php

namespace App\Http\Controllers\Api\V1;

use App\Http\Controllers\Controller;
use App\Http\Requests\Api\V1\StoreOffersRequest;
use App\Http\Resources\OfferBulkResultResource;
use App\Models\CrawlRun;
use App\Models\Offer;
use App\Services\ProductResolver;
use Illuminate\Http\JsonResponse;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Log;
use Throwable;

class CrawlRunOfferController extends Controller
{
    public function __construct(private readonly ProductResolver $resolver) {}

    /**
     * POST /api/v1/crawl-runs/{run}/offers
     *
     * Bulk-push scraped offers. Upserts products implicitly (by external_id
     * or normalized_name) and creates one Offer row per item linked to the
     * run. All-or-nothing transaction — if anything throws mid-batch the
     * entire batch rolls back so the crawler can safely retry.
     *
     * The run's final status is NOT mutated here. The crawler owns lifecycle
     * transitions via PATCH /crawl-runs/{run}; this endpoint stays a pure
     * idempotent data sink. A 5xx response signals the crawler to retry the
     * batch or mark the run failed on its own.
     */
    public function store(StoreOffersRequest $request, CrawlRun $run): JsonResponse
    {
        $payload = $request->validated();
        $brandId = (int) $run->brand_id;

        $persisted = 0;
        $created = 0;
        $updated = 0;

        try {
            DB::transaction(function () use ($payload, $run, $brandId, &$persisted, &$created, &$updated) {
                foreach ($payload['offers'] as $item) {
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
        } catch (Throwable $e) {
            // Transaction is already rolled back by Laravel — nothing was
            // persisted from this batch. Log with enough context to debug
            // (run, brand, batch size, exception class) without leaking
            // payload bodies into logs.
            Log::error('Offer bulk push failed', [
                'run_id' => $run->id,
                'brand_id' => $brandId,
                'batch_size' => count($payload['offers']),
                'exception' => $e::class,
                'message' => $e->getMessage(),
            ]);

            return response()->json([
                'error' => 'offer_push_failed',
                'message' => 'Failed to persist offer batch; nothing was saved. Safe to retry.',
            ], 500);
        }

        return (new OfferBulkResultResource([
            'persisted' => $persisted,
            'products_created' => $created,
            'products_updated' => $updated,
        ]))->response()->setStatusCode(201);
    }
}
