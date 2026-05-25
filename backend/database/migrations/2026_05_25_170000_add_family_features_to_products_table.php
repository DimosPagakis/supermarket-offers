<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

/**
 * Denormalised "family-browse" feature columns on `products`.
 *
 * A family is the deterministic tuple
 *   (manufacturer_brand, category_normalised, size_value, size_unit, pack_count)
 * — see `docs/canonicalisation-design.md` §"A note on family-browse"
 * for the rationale (this is explicitly NOT a canonicalisation reuse).
 *
 * These columns mirror what `crawler/scraper/canonical/extractors.py`
 * derives from product names. They are written by:
 *   - one-time backfill (`php artisan products:enrich-features`), and
 *   - going forward by `App\Services\ProductResolver` on every
 *     find-or-create / update pass.
 *
 * All columns are nullable so existing rows survive the migration; the
 * backfill command fills them on first run.
 */
return new class extends Migration
{
    public function up(): void
    {
        Schema::table('products', function (Blueprint $table) {
            // The manufacturer brand parsed from the name, e.g. "Axe",
            // "Lacta". NULL when the name doesn't lead with a known
            // brand or matches a private-label whitelist (own-brand SKUs
            // never participate in cross-chain family-browse). Stored
            // as the lowercase ASCII-folded canonical key so families
            // are robust across Greek/Latin/case variants.
            $table->string('manufacturer_brand')->nullable()->after('canonical_product_id');

            // Lowercased + accent-folded mirror of `category`. Powers the
            // (manufacturer, category, size) composite index — without
            // folding, Sklavenitis's "ΤΥΡΙΑ" and Masoutis's "Τυριά"
            // would be different families even though they're the same
            // category in the eyes of the shopper.
            $table->string('category_normalised')->nullable()->after('category');

            // Canonical size (numeric value + unit). The crawler
            // extractor produces (float, str) pairs like
            // (150.0, 'ml'), (400.0, 'g'), (1.5, 'l'). NULL when the
            // name carries no recognisable size token.
            $table->decimal('size_value', 10, 3)->nullable()->after('unit');
            $table->string('size_unit', 16)->nullable()->after('size_value');

            // Multi-pack count (default 1). "Coca-Cola 6x330ml" -> 6.
            // Folded with "+N Δώρο" promo packaging — "5x330ml +1 Δώρο"
            // collapses to 6 in the extractor.
            $table->unsignedSmallInteger('pack_count')->default(1)->after('size_unit');

            // What's left after stripping brand+size+pack: the variant
            // tokens that distinguish "Axe Africa" from "Axe Marine".
            // Stored as a deterministic dash-joined slug ("africa"),
            // not as a JSON token set — same reasoning as backend
            // CLAUDE.md "no JSON columns".
            $table->string('variant_descriptor')->nullable()->after('pack_count');
        });

        // Composite index for the families list query — `WHERE
        // manufacturer_brand=? AND category_normalised=? AND size_value=?
        // AND size_unit=?` is the hot path. SQLite gladly uses this
        // for prefix matches too (manufacturer-only filter still hits
        // the leading column).
        Schema::table('products', function (Blueprint $table) {
            $table->index(
                ['manufacturer_brand', 'category_normalised', 'size_value', 'size_unit'],
                'products_family_idx',
            );
            $table->index('manufacturer_brand');
            $table->index('category_normalised');
        });
    }

    public function down(): void
    {
        Schema::table('products', function (Blueprint $table) {
            $table->dropIndex('products_family_idx');
            $table->dropIndex(['manufacturer_brand']);
            $table->dropIndex(['category_normalised']);
            $table->dropColumn([
                'manufacturer_brand',
                'category_normalised',
                'size_value',
                'size_unit',
                'pack_count',
                'variant_descriptor',
            ]);
        });
    }
};
