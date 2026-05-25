<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Builder;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;

class CrawlRun extends Model
{
    public const STATUS_RUNNING = 'running';
    public const STATUS_SUCCESS = 'success';
    public const STATUS_FAILED = 'failed';
    public const STATUS_PARTIAL = 'partial';

    /** Terminal statuses — runs in these states are immutable. */
    public const TERMINAL_STATUSES = [
        self::STATUS_SUCCESS,
        self::STATUS_FAILED,
        self::STATUS_PARTIAL,
    ];

    /** Acceptable values for the `triggered_by` audit column. */
    public const TRIGGER_SOURCES = ['schedule', 'manual', 'api'];

    protected $fillable = [
        'brand_id',
        'started_at',
        'finished_at',
        'status',
        'offers_found',
        'offers_persisted',
        'error_message',
        'triggered_by',
    ];

    protected $casts = [
        'started_at' => 'datetime',
        'finished_at' => 'datetime',
        'offers_found' => 'integer',
        'offers_persisted' => 'integer',
    ];

    public function brand(): BelongsTo
    {
        return $this->belongsTo(Brand::class);
    }

    public function offers(): HasMany
    {
        return $this->hasMany(Offer::class);
    }
}
