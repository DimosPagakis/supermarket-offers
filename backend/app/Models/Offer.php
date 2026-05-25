<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Builder;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Query\Builder as QueryBuilder;
use Illuminate\Support\Facades\DB;

class Offer extends Model
{
    protected $fillable = [
        'product_id',
        'crawl_run_id',
        'price',
        'original_price',
        'discount_pct',
        'promo_label',
        'promo_type',
        'currency',
        'valid_from',
        'valid_to',
        'scraped_at',
    ];

    /**
     * Allowed values for the structured `promo_type` column.
     *
     * Stays in sync with {@see \App\Http\Requests\Api\V1\StoreOffersRequest}.
     * `loyalty_points` is reserved for future use — we don't currently emit
     * loyalty-only offers (see `crawler/scraper/parsers/ab.py` family
     * docstring) but keeping it on the enum means a parser change doesn't
     * need a backend migration.
     */
    public const PROMO_TYPES = [
        'strikethrough',
        'bxgy_free',
        'bxg_percent',
        'discount_euros',
        'loyalty_points',
    ];

    protected $casts = [
        'price' => 'decimal:2',
        'original_price' => 'decimal:2',
        'discount_pct' => 'integer',
        'valid_from' => 'date',
        'valid_to' => 'date',
        'scraped_at' => 'datetime',
    ];

    public function product(): BelongsTo
    {
        return $this->belongsTo(Product::class);
    }

    public function crawlRun(): BelongsTo
    {
        return $this->belongsTo(CrawlRun::class);
    }

    /**
     * Pick the latest offer id per product_id from a filtered offer set.
     *
     * Uses MAX(offers.id) GROUP BY product_id rather than a window function
     * so the path works identically on SQLite and Postgres without raw SQL.
     * MAX(id) (not MAX(scraped_at)) keeps the result deterministic when
     * two offers for the same product share scraped_at — ids are
     * monotonic so the higher id is the more recently inserted row.
     *
     * Callers pass a query that already carries every active filter, and
     * use the returned subquery via `whereIn('offers.id', …)` to collapse
     * the filtered set to one row per product.
     */
    public static function latestPerProductIds(Builder $filtered): Builder|QueryBuilder
    {
        return (clone $filtered)
            ->select(DB::raw('MAX(offers.id) as id'))
            ->groupBy('offers.product_id');
    }
}
