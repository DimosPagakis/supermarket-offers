<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;

class Product extends Model
{
    protected $fillable = [
        'brand_id',
        'external_id',
        'name',
        'normalized_name',
        'url',
        'image_url',
        'category',
        'unit',
        'canonical_product_id',
        'canonical_match_confidence',
        'canonical_match_method',
        'canonical_matched_at',
    ];

    protected $casts = [
        'canonical_match_confidence' => 'decimal:3',
        'canonical_matched_at' => 'datetime',
    ];

    public function brand(): BelongsTo
    {
        return $this->belongsTo(Brand::class);
    }

    public function offers(): HasMany
    {
        return $this->hasMany(Offer::class);
    }

    public function canonicalProduct(): BelongsTo
    {
        return $this->belongsTo(CanonicalProduct::class);
    }
}
