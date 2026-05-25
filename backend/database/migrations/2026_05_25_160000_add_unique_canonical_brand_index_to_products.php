<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Support\Facades\DB;

/**
 * Phase 2.1 over-merge guardrail.
 *
 * A canonical product is meant to represent ONE SKU across multiple
 * chains — i.e. at most one member product per brand. A live audit on
 * 2026-05-25 found 78% (1,151 / 1,465) of canonicals violated that
 * invariant, with up to 30 same-brand member rows collapsed into one
 * canonical (Axe deodorant scents, Ariel pods variants, Ajax cleaner
 * scents).
 *
 * Crawler-side fixes (disjoint-token rejection, max_block_size=8,
 * auto-merge-cosine=0.97) address the algorithm; this index is the
 * database-level safety net so a bad re-run cannot silently re-introduce
 * the bug. The bulk-upsert action catches the constraint violation,
 * logs a structured warning, and skips the offending member rather than
 * failing the whole batch (see BulkUpsertCanonicalProducts).
 *
 * Partial index: only enforced on rows that are actually assigned to a
 * canonical. Unassigned products (canonical_product_id NULL) are free
 * to be many-per-brand. The ``WHERE …`` clause works on both SQLite
 * (≥3.8) and Postgres, which is all we run.
 */
return new class extends Migration
{
    public function up(): void
    {
        DB::statement(
            'CREATE UNIQUE INDEX IF NOT EXISTS '.
            'products_canonical_brand_unique '.
            'ON products(canonical_product_id, brand_id) '.
            'WHERE canonical_product_id IS NOT NULL'
        );
    }

    public function down(): void
    {
        DB::statement('DROP INDEX IF EXISTS products_canonical_brand_unique');
    }
};
