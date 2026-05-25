<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Log;

/**
 * One-shot cleanup of catalogue-leak offer rows accumulated before the
 * discounted-only emit policy landed (2026-05-25).
 *
 * Pre-policy the per-brand parsers (Lidl, Masoutis, My Market,
 * Sklavenitis) emitted every row they saw, including the chain's full
 * active catalogue. The public ``/api/public/v1/offers`` endpoint then
 * served those rows as "offers" alongside the real flyer items. Of
 * 12,105 offers in the live DB at the time of writing, only 682 (5.6%)
 * carried any discount signal.
 *
 * This migration deletes every row that fails the same promo-signal
 * check the new ``StoreOffersRequest::offerCarriesPromoSignal()``
 * enforces on ingest:
 *
 *   discount_pct IS NULL OR discount_pct = 0,
 *   AND promo_label IS NULL (treat blanks as null — column is varchar),
 *   AND (original_price IS NULL OR original_price <= price)
 *
 * The deletion cascades to nothing — offers are leaf rows. Affected
 * products stay in the DB; they simply no longer have a current offer
 * surfacing on the public API.
 *
 * Down() is intentionally a no-op. Deleted rows are not recoverable
 * from the schema alone, and replaying historical catalogue-leaks
 * would re-introduce the exact bug this migration cleans up. If a
 * down-migrate is required, restore from a backup.
 */
return new class extends Migration
{
    public function up(): void
    {
        $deleted = DB::table('offers')
            ->where(function ($q) {
                $q->whereNull('discount_pct')->orWhere('discount_pct', 0);
            })
            ->where(function ($q) {
                // Treat empty strings as null — the column is a varchar
                // and either shape is possible depending on driver.
                $q->whereNull('promo_label')->orWhere('promo_label', '');
            })
            ->where(function ($q) {
                $q->whereNull('original_price')
                    ->orWhereColumn('original_price', '<=', 'price');
            })
            ->delete();

        Log::info(
            'delete_catalogue_leak_offers: removed {count} catalogue-leak '.
            'offer rows (no discount_pct, no promo_label, no strikethrough)',
            ['count' => $deleted],
        );

        // Database-level backstop: a trigger that aborts any INSERT
        // that would create a no-promo-signal row. The
        // StoreOffersRequest catches it earlier (HTTP 422), but if a
        // future code path bypasses the FormRequest (artisan tinker,
        // a direct DB::table('offers')->insert()), this trigger still
        // refuses the write. We currently run on SQLite only (see
        // backend/CLAUDE.md "Why SQLite by default") so use the SQLite
        // ``RAISE(ABORT, …)`` form. When we migrate to Postgres, swap
        // this for an equivalent ``CREATE FUNCTION`` + trigger or a
        // proper ``CHECK`` constraint (Postgres supports both on
        // ALTER TABLE; SQLite does not).
        DB::statement('DROP TRIGGER IF EXISTS offers_require_promo_signal');
        DB::statement(
            "CREATE TRIGGER offers_require_promo_signal\n".
            "BEFORE INSERT ON offers\n".
            "FOR EACH ROW\n".
            "WHEN (NEW.discount_pct IS NULL OR NEW.discount_pct = 0)\n".
            "  AND (NEW.promo_label IS NULL OR NEW.promo_label = '')\n".
            "  AND (NEW.original_price IS NULL OR NEW.original_price <= NEW.price)\n".
            "BEGIN\n".
            "  SELECT RAISE(ABORT, 'offers row missing promo signal: ".
            "need discount_pct>0, promo_label, or original_price>price');\n".
            "END;"
        );
    }

    public function down(): void
    {
        // The DELETE is intentionally a one-way op — see the class
        // docblock. We do drop the trigger so a future rollback can
        // reshape the schema cleanly.
        DB::statement('DROP TRIGGER IF EXISTS offers_require_promo_signal');
    }
};
