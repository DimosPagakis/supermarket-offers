<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

/**
 * Create the canonicalisation destination table and finish wiring the FK
 * from products.
 *
 * Background: `products.canonical_product_id` already exists as a nullable
 * column (added in the products migration) so the cross-brand comparison
 * surface can land without a backfill blocking it. This migration:
 *
 *   1. Creates the `canonical_products` table — the natural key is
 *      `canonical_key`, a deterministic ID like `lacta:gofreta-foundouki:31g:1`
 *      that the algorithm side computes. We don't try to enforce a parser
 *      contract here — the column is opaque to the backend and only the
 *      crawler-side canonicaliser cares about its structure.
 *   2. Turns the existing `products.canonical_product_id` column into a
 *      proper foreign key + adds the three audit columns the algorithm
 *      writes alongside each assignment (confidence, method, matched_at).
 *      The existing single-column index on the products table is left
 *      untouched.
 *
 * See `docs/canonicalisation-design.md` §5 for the schema motivation.
 */
return new class extends Migration
{
    public function up(): void
    {
        Schema::create('canonical_products', function (Blueprint $table): void {
            $table->id();
            // Deterministic, opaque-to-the-backend natural key. UNIQUE so a
            // re-upsert from the algorithm is idempotent and we never end
            // up with duplicate canonicals for the same SKU.
            $table->string('canonical_key')->unique();

            // The manufacturer brand parsed by the algorithm. Required —
            // without it we cannot enforce the "same brand + different
            // size = different canonical" rule that the design doc calls
            // out as non-negotiable. Stored as free-text (case the
            // algorithm chose); compared exactly.
            $table->string('manufacturer_brand');

            // Package size + unit. Nullable because the algorithm may
            // fall back to a no-size canonical for items where the SKU
            // identity is the variant alone (e.g. fresh meat by weight).
            $table->decimal('size_value', 10, 3)->nullable();
            $table->string('size_unit', 16)->nullable();
            $table->unsignedSmallInteger('pack_count')->default(1);

            // Variant descriptor (flavour, colour, scent, etc.). Optional;
            // every canonical product is uniquely identified by the
            // canonical_key, this just makes the row human-readable.
            $table->string('variant_descriptor')->nullable();

            // Display name + category drive the public read API. We
            // refresh display_name on upsert if a "richer" member arrives
            // (see CanonicalProduct::refreshAggregates()).
            $table->string('display_name');
            $table->string('category')->nullable();
            $table->string('image_url')->nullable();

            // Denormalised counts — recomputed by refreshAggregates() at
            // the end of every bulk-upsert. Kept on the row so the
            // comparison list query (sort/filter by brands_count or
            // members_count) doesn't have to join + group on every
            // request.
            $table->unsignedSmallInteger('members_count')->default(0);
            $table->unsignedSmallInteger('brands_count')->default(0);

            $table->timestamps();

            $table->index('manufacturer_brand');
            $table->index('category');
            // The top-N coverage queries (the comparison list view) sort
            // by brands_count desc then members_count desc; the composite
            // matches that ordering on both SQLite and Postgres.
            $table->index(['brands_count', 'members_count']);
        });

        Schema::table('products', function (Blueprint $table): void {
            // Promote the existing canonical_product_id column to a proper
            // FK with set-null on delete. The plain index already exists
            // from the create_products migration; we deliberately do not
            // re-add it.
            $table->foreign('canonical_product_id')
                ->references('id')
                ->on('canonical_products')
                ->nullOnDelete();

            // Per-assignment audit trail. confidence is [0,1] (decimal so
            // the storage is exact); method records which pipeline stage
            // produced the assignment ('rule'|'embedding'|'llm'|'manual')
            // and matched_at is when it landed. Together they let the
            // bulk-upsert endpoint stay idempotent without overwriting a
            // higher-confidence existing assignment.
            $table->decimal('canonical_match_confidence', 4, 3)->nullable();
            $table->string('canonical_match_method')->nullable();
            $table->timestamp('canonical_matched_at')->nullable();
        });
    }

    public function down(): void
    {
        Schema::table('products', function (Blueprint $table): void {
            $table->dropForeign(['canonical_product_id']);
            $table->dropColumn([
                'canonical_match_confidence',
                'canonical_match_method',
                'canonical_matched_at',
            ]);
        });

        Schema::dropIfExists('canonical_products');
    }
};
