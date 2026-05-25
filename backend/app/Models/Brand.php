<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\HasMany;
use Illuminate\Database\Eloquent\Relations\HasOne;

class Brand extends Model
{
    protected $fillable = [
        'name',
        'slug',
        'website_url',
        'country_code',
        'active',
    ];

    protected $casts = [
        'active' => 'boolean',
    ];

    public function crawlConfig(): HasOne
    {
        return $this->hasOne(CrawlConfig::class);
    }

    public function crawlRuns(): HasMany
    {
        return $this->hasMany(CrawlRun::class);
    }

    public function products(): HasMany
    {
        return $this->hasMany(Product::class);
    }

    public function lastSuccessfulRun(): HasOne
    {
        return $this->hasOne(CrawlRun::class)
            ->where('status', 'success')
            ->latestOfMany('finished_at');
    }
}
