<?php

namespace App\Http\Controllers\Api\V1;

use App\Domain\Canonical\BulkUpsertCanonicalProducts;
use App\Http\Controllers\Controller;
use App\Http\Requests\Api\V1\BulkUpsertCanonicalProductsRequest;
use Illuminate\Http\JsonResponse;
use Illuminate\Support\Facades\Log;
use Throwable;

class CanonicalProductController extends Controller
{
    public function __construct(private readonly BulkUpsertCanonicalProducts $action) {}

    /**
     * POST /api/v1/canonical-products/bulk-upsert
     *
     * Pure HTTP shell: validate, delegate to the action (which owns
     * the transaction + business logic), and wrap the outcome in the
     * standard JSON envelope. The all-or-nothing rollback and the
     * idempotent-by-canonical_key contract live in
     * {@see BulkUpsertCanonicalProducts}.
     *
     * Any uncaught Throwable from the action means the transaction
     * already rolled back; we surface a structured 500 with a
     * "Safe to retry" hint that mirrors the offer-push contract so
     * the canonicaliser can replay the same batch.
     */
    public function bulkUpsert(BulkUpsertCanonicalProductsRequest $request): JsonResponse
    {
        $payload = $request->validated();

        try {
            $result = ($this->action)($payload['groupings']);
        } catch (Throwable $e) {
            Log::error('Canonical bulk upsert failed', [
                'groupings' => count($payload['groupings'] ?? []),
                'exception' => $e::class,
                'message' => $e->getMessage(),
            ]);

            return response()->json([
                'error' => 'canonical_bulk_upsert_failed',
                'message' => 'Failed to persist canonical groupings; nothing was saved. Safe to retry.',
            ], 500);
        }

        return response()->json($result->toArray(), 200);
    }
}
