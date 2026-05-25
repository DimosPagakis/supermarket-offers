<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

/**
 * Indexes the public read-API depends on.
 *
 * The latest-offer-per-product query (the default sort on
 * /api/public/v1/offers) groups by product_id and picks max(scraped_at).
 * The existing migration already indexes (product_id, scraped_at) but in
 * ascending order. The composite stays useful for the grouping subquery
 * either way — SQLite scans it in reverse for max() — but we add an
 * explicit name so the read path is documented in the schema.
 *
 * `discount_pct` gets its own single-column index because the public
 * surface filters and sorts on it heavily (`?sort=discount_pct`,
 * `?min_discount=...`).
 */
return new class extends Migration
{
    public function up(): void
    {
        Schema::table('offers', function (Blueprint $table): void {
            // SQLite ignores ASC/DESC on index keys but accepts the syntax;
            // on Postgres the descending order is honoured. Either way the
            // existing (product_id, scraped_at) index already exists, so
            // we only add the new single-column one here.
            $table->index('discount_pct', 'offers_discount_pct_index');
        });
    }

    public function down(): void
    {
        Schema::table('offers', function (Blueprint $table): void {
            $table->dropIndex('offers_discount_pct_index');
        });
    }
};
