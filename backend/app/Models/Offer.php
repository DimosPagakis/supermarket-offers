<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class Offer extends Model
{
    protected $fillable = [
        'product_id',
        'crawl_run_id',
        'price',
        'original_price',
        'discount_pct',
        'currency',
        'valid_from',
        'valid_to',
        'scraped_at',
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
}
