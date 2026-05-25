<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

/**
 * Adds the `promo_label` and `promo_type` columns to the `offers` table.
 *
 * These exist to faithfully represent non-strikethrough promotions (BOGOF,
 * multi-buy %, multi-buy €) on the frontend without lying about the
 * per-unit price. The shopper-facing label ("1+1 δώρο", "-30% στα 2") is
 * carried verbatim; the structured `promo_type` lets clients branch on
 * the kind of deal without parsing Greek copy.
 *
 * Both columns are nullable — strikethrough-only legacy data and brands
 * that don't ship rich promo metadata (Sklavenitis / My Market) leave
 * them null. The contract change is additive: existing consumers see
 * `null` and ignore them.
 */
return new class extends Migration
{
    public function up(): void
    {
        Schema::table('offers', function (Blueprint $table) {
            $table->string('promo_label', 80)->nullable()->after('discount_pct');
            $table->string('promo_type', 32)->nullable()->after('promo_label');
            $table->index('promo_type');
        });
    }

    public function down(): void
    {
        Schema::table('offers', function (Blueprint $table) {
            $table->dropIndex(['promo_type']);
            $table->dropColumn(['promo_label', 'promo_type']);
        });
    }
};
