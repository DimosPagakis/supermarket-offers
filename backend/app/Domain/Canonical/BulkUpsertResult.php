<?php

namespace App\Domain\Canonical;

/**
 * Outcome of a canonical bulk-upsert batch.
 *
 * Mirrors the wire shape of the controller's JSON response so the
 * HTTP layer is a pass-through. `errors` is a list of structured
 * dictionaries (grouping_index, member_index, product_id, reason) for
 * non-fatal per-member problems the caller should surface — anything
 * fatal would have thrown and rolled the transaction back instead.
 *
 * Phase 2.1: ``duplicateBrandSkipped`` counts members rejected by the
 * ``products_canonical_brand_unique`` partial index, i.e. a canonical
 * already holds a member from this brand. The action logs each skip
 * and continues; this counter surfaces the count in the response
 * envelope so the crawler can spot a leaking algorithm at a glance.
 * Backwards-compatible: existing clients that ignore unknown fields
 * are unaffected.
 */
final readonly class BulkUpsertResult
{
    /**
     * @param  array<int, array<string, mixed>>  $errors
     */
    public function __construct(
        public int $created,
        public int $updated,
        public int $productsAssigned,
        public array $errors,
        public int $duplicateBrandSkipped = 0,
    ) {}

    /**
     * @return array{
     *     created: int,
     *     updated: int,
     *     products_assigned: int,
     *     errors: array<int, array<string, mixed>>,
     *     duplicate_brand_skipped: int,
     * }
     */
    public function toArray(): array
    {
        return [
            'created' => $this->created,
            'updated' => $this->updated,
            'products_assigned' => $this->productsAssigned,
            'errors' => $this->errors,
            'duplicate_brand_skipped' => $this->duplicateBrandSkipped,
        ];
    }
}
