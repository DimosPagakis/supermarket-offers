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

class CrawlRunOfferController extends Controller
{
    public function __construct(private readonly ProductResolver $resolver) {}

    /**
     * POST /api/v1/crawl-runs/{run}/offers
     *
     * Bulk-push scraped offers. Upserts products implicitly (by external_id
     * or normalized_name) and creates one Offer row per item linked to the
     * run. All-or-nothing transaction.
     */
    public function store(StoreOffersRequest $request, CrawlRun $run): JsonResponse
    {
        $payload = $request->validated();
        $brandId = (int) $run->brand_id;

        $persisted = 0;
        $created = 0;
        $updated = 0;

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

        return (new OfferBulkResultResource([
            'persisted' => $persisted,
            'products_created' => $created,
            'products_updated' => $updated,
        ]))->response()->setStatusCode(201);
    }
}
