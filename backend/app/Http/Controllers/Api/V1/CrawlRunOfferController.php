<?php

namespace App\Http\Controllers\Api\V1;

use App\Domain\Offer\IngestOffers;
use App\Http\Controllers\Controller;
use App\Http\Requests\Api\V1\StoreOffersRequest;
use App\Http\Resources\OfferBulkResultResource;
use App\Models\CrawlRun;
use Illuminate\Http\JsonResponse;
use Illuminate\Support\Facades\Log;
use Throwable;

class CrawlRunOfferController extends Controller
{
    public function __construct(private readonly IngestOffers $ingest) {}

    /**
     * POST /api/v1/crawl-runs/{run}/offers
     *
     * Pure HTTP shell: validate, delegate to the action (which owns
     * the transaction + product resolution + offer persistence), and
     * wrap the outcome in the standard JSON envelope. The
     * all-or-nothing rollback and the idempotent product-matching
     * contract live in {@see IngestOffers}.
     *
     * The run's final status is NOT mutated here. The crawler owns
     * lifecycle transitions via PATCH /crawl-runs/{run}; this
     * endpoint stays a pure idempotent data sink. Any uncaught
     * Throwable from the action means the transaction already rolled
     * back; we surface a structured 500 with a "Safe to retry" hint
     * so the crawler can replay the same batch.
     */
    public function store(StoreOffersRequest $request, CrawlRun $run): JsonResponse
    {
        $payload = $request->validated();

        try {
            $result = ($this->ingest)($run, $payload['offers']);
        } catch (Throwable $e) {
            // Transaction is already rolled back by the action — nothing
            // was persisted from this batch. Log with enough context to
            // debug without leaking payload bodies into logs.
            Log::error('Offer bulk push failed', [
                'run_id' => $run->id,
                'brand_id' => (int) $run->brand_id,
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
            'persisted' => $result->persisted,
            'products_created' => $result->productsCreated,
            'products_updated' => $result->productsUpdated,
        ]))->response()->setStatusCode(201);
    }
}
