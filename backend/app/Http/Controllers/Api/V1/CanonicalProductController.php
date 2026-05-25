<?php

namespace App\Http\Controllers\Api\V1;

use App\Http\Controllers\Controller;
use App\Http\Requests\Api\V1\BulkUpsertCanonicalProductsRequest;
use App\Models\CanonicalProduct;
use App\Models\Product;
use Illuminate\Http\JsonResponse;
use Illuminate\Support\Carbon;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Log;
use Throwable;

class CanonicalProductController extends Controller
{
    /**
     * POST /api/v1/canonical-products/bulk-upsert
     *
     * The canonicaliser (a script in the crawler workspace) computes
     * groupings offline and pushes them here. The endpoint:
     *
     *   1. Upserts one `canonical_products` row per grouping, keyed by
     *      `canonical_key`. On update we refresh the human-readable
     *      fields (display_name, variant_descriptor, image_url) — the
     *      algorithm is the source of truth for these.
     *   2. Per member: stamp `products.canonical_product_id` plus the
     *      audit columns (confidence, method, matched_at), but only if
     *      the existing assignment's confidence is lower or absent. A
     *      manual reviewer's 1.0 assignment is never silently
     *      overwritten by a later rule-based 0.98.
     *   3. After all groupings: recompute aggregates for every affected
     *      canonical so the public list view's brands_count /
     *      members_count are current.
     *
     * Wrapped in a single transaction: if anything throws, nothing
     * lands. Mirrors the all-or-nothing offer-push contract — the
     * canonicaliser retries the whole batch.
     */
    public function bulkUpsert(BulkUpsertCanonicalProductsRequest $request): JsonResponse
    {
        $payload = $request->validated();

        $created = 0;
        $updated = 0;
        $productsAssigned = 0;
        $errors = [];

        try {
            DB::transaction(function () use ($payload, &$created, &$updated, &$productsAssigned, &$errors): void {
                /** @var array<int, CanonicalProduct> $touched */
                $touched = [];

                foreach ($payload['groupings'] as $i => $grouping) {
                    $existing = CanonicalProduct::query()
                        ->where('canonical_key', $grouping['canonical_key'])
                        ->first();

                    $attributes = [
                        'canonical_key' => $grouping['canonical_key'],
                        'manufacturer_brand' => $grouping['manufacturer_brand'],
                        'size_value' => $grouping['size_value'] ?? null,
                        'size_unit' => $grouping['size_unit'] ?? null,
                        'pack_count' => $grouping['pack_count'] ?? 1,
                        'variant_descriptor' => $grouping['variant_descriptor'] ?? null,
                        'display_name' => $grouping['display_name'],
                        'category' => $grouping['category'] ?? null,
                    ];

                    // image_url: only overwrite an existing canonical's
                    // image when the algorithm explicitly sends a new
                    // one. Aggregates refresh below will lazily backfill
                    // from a member if both are still null.
                    if (array_key_exists('image_url', $grouping) && $grouping['image_url'] !== null) {
                        $attributes['image_url'] = $grouping['image_url'];
                    }

                    if ($existing === null) {
                        $canonical = CanonicalProduct::create($attributes);
                        $created++;
                    } else {
                        $existing->fill($attributes);
                        $isDirty = $existing->isDirty();
                        $existing->save();
                        $canonical = $existing;
                        if ($isDirty) {
                            $updated++;
                        }
                    }

                    $touched[$canonical->id] = $canonical;

                    // Idempotent member assignment: only stamp the
                    // product if the new confidence beats the existing
                    // one (or there is no existing assignment).
                    $memberIds = array_column($grouping['members'], 'product_id');
                    $existingProducts = Product::query()
                        ->whereIn('id', $memberIds)
                        ->get()
                        ->keyBy('id');

                    foreach ($grouping['members'] as $j => $member) {
                        $productId = (int) $member['product_id'];
                        $product = $existingProducts->get($productId);

                        if ($product === null) {
                            $errors[] = [
                                'grouping_index' => $i,
                                'member_index' => $j,
                                'product_id' => $productId,
                                'reason' => 'product_not_found',
                            ];

                            continue;
                        }

                        $newConfidence = (float) $member['confidence'];
                        $existingConfidence = $product->canonical_match_confidence !== null
                            ? (float) $product->canonical_match_confidence
                            : null;

                        // Skip if an existing assignment has strictly
                        // higher confidence. Equal confidence still
                        // wins (refresh matched_at, preserve idempotent
                        // re-pushes).
                        if (
                            $product->canonical_product_id !== null
                            && $existingConfidence !== null
                            && $existingConfidence > $newConfidence
                        ) {
                            continue;
                        }

                        // If the product was previously assigned to a
                        // *different* canonical, the old canonical's
                        // counts will be stale after this. Touch it so
                        // the aggregate refresh covers it too.
                        if (
                            $product->canonical_product_id !== null
                            && (int) $product->canonical_product_id !== $canonical->id
                        ) {
                            $previous = CanonicalProduct::find($product->canonical_product_id);
                            if ($previous !== null) {
                                $touched[$previous->id] = $previous;
                            }
                        }

                        $product->canonical_product_id = $canonical->id;
                        $product->canonical_match_confidence = $newConfidence;
                        $product->canonical_match_method = $member['match_method'];
                        $product->canonical_matched_at = Carbon::now();
                        $product->save();

                        $productsAssigned++;
                    }
                }

                foreach ($touched as $canonical) {
                    $canonical->refreshAggregates();
                }
            });
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

        return response()->json([
            'created' => $created,
            'updated' => $updated,
            'products_assigned' => $productsAssigned,
            'errors' => $errors,
        ], 200);
    }
}
