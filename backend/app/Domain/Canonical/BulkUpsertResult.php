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
    ) {}

    /**
     * @return array{created: int, updated: int, products_assigned: int, errors: array<int, array<string, mixed>>}
     */
    public function toArray(): array
    {
        return [
            'created' => $this->created,
            'updated' => $this->updated,
            'products_assigned' => $this->productsAssigned,
            'errors' => $this->errors,
        ];
    }
}
