<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class CrawlConfig extends Model
{
    protected $fillable = [
        'brand_id',
        'strategy',
        'start_url',
        'rate_limit_ms',
        'respect_robots_txt',
        'cache_ttl_seconds',
        'schedule_cron',
    ];

    protected $casts = [
        'respect_robots_txt' => 'boolean',
        'rate_limit_ms' => 'integer',
        'cache_ttl_seconds' => 'integer',
    ];

    public function brand(): BelongsTo
    {
        return $this->belongsTo(Brand::class);
    }
}
