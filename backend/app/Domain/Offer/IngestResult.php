<?php

namespace App\Domain\Offer;

/**
 * Outcome of an offer ingest batch.
 *
 * Mirrors the wire shape returned by POST /crawl-runs/{run}/offers so
 * the HTTP layer is a pass-through. Counts are populated by the
 * action; on failure the action throws and the controller's outer
 * envelope handles the 500 — nothing partial reaches the wire.
 */
final readonly class IngestResult
{
    public function __construct(
        public int $persisted,
        public int $productsCreated,
        public int $productsUpdated,
    ) {}

    /**
     * @return array{persisted: int, products_created: int, products_updated: int}
     */
    public function toArray(): array
    {
        return [
            'persisted' => $this->persisted,
            'products_created' => $this->productsCreated,
            'products_updated' => $this->productsUpdated,
        ];
    }
}
