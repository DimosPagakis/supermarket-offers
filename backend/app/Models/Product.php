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
        // Family-browse denormalised features (see VariantDescriber +
        // 2026_05_25_170000_add_family_features_to_products_table).
        'manufacturer_brand',
        'category_normalised',
        'size_value',
        'size_unit',
        'pack_count',
        'variant_descriptor',
    ];

    protected $casts = [
        'canonical_match_confidence' => 'decimal:3',
        'canonical_matched_at' => 'datetime',
        'size_value' => 'decimal:3',
        'pack_count' => 'integer',
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
