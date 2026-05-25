<?php

namespace App\Domain\Canonical;

use App\Models\CanonicalProduct;
use App\Models\Product;
use Illuminate\Database\UniqueConstraintViolationException;
use Illuminate\Support\Carbon;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Log;

/**
 * Apply a batch of canonical groupings to the database.
 *
 *   1. Upserts one `canonical_products` row per grouping, keyed by
 *      `canonical_key`. Human-readable fields (display_name,
 *      variant_descriptor, image_url, …) get refreshed on update —
 *      the algorithm is the source of truth for them.
 *   2. Per member: stamps `products.canonical_product_id` plus the
 *      audit columns, but only if the existing assignment's confidence
 *      is lower or absent. A manual reviewer's 1.0 is never silently
 *      overwritten by a later 0.98 rule pass.
 *   3. After all groupings, refreshes denormalised counts on every
 *      affected canonical (including any previous canonicals members
 *      were re-pointed away from).
 *
 * Runs inside a single transaction — any exception rolls everything
 * back so the canonicaliser can safely retry the whole batch. The
 * outer envelope (HTTP status, error JSON) is the caller's concern;
 * this action only signals failure by letting the exception
 * propagate.
 */
class BulkUpsertCanonicalProducts
{
    /**
     * @param  array<int, array<string, mixed>>  $groupings  validated payload
     */
    public function __invoke(array $groupings): BulkUpsertResult
    {
        $created = 0;
        $updated = 0;
        $productsAssigned = 0;
        $duplicateBrandSkipped = 0;
        $errors = [];

        DB::transaction(function () use ($groupings, &$created, &$updated, &$productsAssigned, &$duplicateBrandSkipped, &$errors): void {
            /** @var array<int, CanonicalProduct> $touched */
            $touched = [];

            foreach ($groupings as $i => $grouping) {
                $canonical = $this->upsertCanonical($grouping, $created, $updated);
                $touched[$canonical->id] = $canonical;

                $this->assignMembers(
                    grouping: $grouping,
                    canonical: $canonical,
                    groupingIndex: $i,
                    productsAssigned: $productsAssigned,
                    duplicateBrandSkipped: $duplicateBrandSkipped,
                    errors: $errors,
                    touched: $touched,
                );
            }

            foreach ($touched as $canonical) {
                $canonical->refreshAggregates();
            }
        });

        return new BulkUpsertResult(
            created: $created,
            updated: $updated,
            productsAssigned: $productsAssigned,
            errors: $errors,
            duplicateBrandSkipped: $duplicateBrandSkipped,
        );
    }

    /**
     * Upsert the canonical_products row by `canonical_key`. Bumps the
     * caller's `$created` / `$updated` counters.
     *
     * @param  array<string, mixed>  $grouping
     */
    private function upsertCanonical(array $grouping, int &$created, int &$updated): CanonicalProduct
    {
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

        // image_url: only overwrite an existing canonical's image when
        // the algorithm explicitly sends a new one. Aggregates refresh
        // below will lazily backfill from a member if both are still null.
        if (array_key_exists('image_url', $grouping) && $grouping['image_url'] !== null) {
            $attributes['image_url'] = $grouping['image_url'];
        }

        if ($existing === null) {
            $created++;

            return CanonicalProduct::create($attributes);
        }

        $existing->fill($attributes);
        if ($existing->isDirty()) {
            $updated++;
        }
        $existing->save();

        return $existing;
    }

    /**
     * Stamp the canonical FK + audit columns on each member product,
     * honouring the confidence-arbitration rule. Records non-fatal
     * `product_not_found` issues in `$errors` and accumulates any
     * previously-owned canonical into `$touched` so its aggregates get
     * refreshed at end-of-batch.
     *
     * @param  array<string, mixed>  $grouping
     * @param  array<int, array<string, mixed>>  $errors
     * @param  array<int, CanonicalProduct>  $touched
     */
    private function assignMembers(
        array $grouping,
        CanonicalProduct $canonical,
        int $groupingIndex,
        int &$productsAssigned,
        int &$duplicateBrandSkipped,
        array &$errors,
        array &$touched,
    ): void {
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
                    'grouping_index' => $groupingIndex,
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

            // Skip if an existing assignment has strictly higher confidence.
            // Equal confidence still wins (refresh matched_at, preserve
            // idempotent re-pushes).
            if (
                $product->canonical_product_id !== null
                && $existingConfidence !== null
                && $existingConfidence > $newConfidence
            ) {
                continue;
            }

            // If the product was previously assigned to a *different*
            // canonical, the old canonical's counts will be stale after
            // this. Touch it so the aggregate refresh covers it too.
            $previousCanonicalId = $product->canonical_product_id !== null
                && (int) $product->canonical_product_id !== $canonical->id
                ? (int) $product->canonical_product_id
                : null;
            if ($previousCanonicalId !== null) {
                $previous = CanonicalProduct::find($previousCanonicalId);
                if ($previous !== null) {
                    $touched[$previous->id] = $previous;
                }
            }

            $product->canonical_product_id = $canonical->id;
            $product->canonical_match_confidence = $newConfidence;
            $product->canonical_match_method = $member['match_method'];
            $product->canonical_matched_at = Carbon::now();

            // Phase 2.1 guardrail: the partial unique index
            // ``products_canonical_brand_unique`` rejects a second
            // product from the same brand against the same canonical.
            // Wrap the save in a savepoint so a violation doesn't
            // poison the outer transaction — we log, skip the loser,
            // and keep processing the rest of the batch.
            try {
                DB::transaction(function () use ($product): void {
                    $product->save();
                });
            } catch (UniqueConstraintViolationException $e) {
                // The model state was mutated in-memory before the
                // save attempt; refresh so callers (and tests) see
                // the pre-save state.
                $product->refresh();

                $winner = Product::query()
                    ->where('canonical_product_id', $canonical->id)
                    ->where('brand_id', $product->brand_id)
                    ->whereKeyNot($product->id)
                    ->first();

                Log::warning('canonical_bulk_upsert.duplicate_brand_skipped', [
                    'canonical_id' => $canonical->id,
                    'canonical_key' => $canonical->canonical_key,
                    'brand_id' => $product->brand_id,
                    'skipped_product_id' => $product->id,
                    'existing_product_id' => $winner?->id,
                    'grouping_index' => $groupingIndex,
                    'member_index' => $j,
                ]);

                $duplicateBrandSkipped++;

                continue;
            }

            $productsAssigned++;
        }
    }
}
