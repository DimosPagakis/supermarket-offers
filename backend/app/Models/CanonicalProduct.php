<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\HasMany;
use Illuminate\Support\Facades\DB;

/**
 * A canonical product — one row per physical SKU across all chains.
 *
 * The natural key is `canonical_key`, a deterministic ID the
 * algorithm-side canonicaliser computes (see
 * `docs/canonicalisation-design.md`). Members are the per-chain
 * `products` rows that the algorithm assigned to this canonical via a
 * bulk-upsert call.
 *
 * Denormalised counts (`members_count`, `brands_count`) are refreshed by
 * the bulk-upsert endpoint after each batch — see refreshAggregates().
 */
class CanonicalProduct extends Model
{
    protected $fillable = [
        'canonical_key',
        'manufacturer_brand',
        'size_value',
        'size_unit',
        'pack_count',
        'variant_descriptor',
        'display_name',
        'category',
        'image_url',
        'members_count',
        'brands_count',
    ];

    protected $casts = [
        'size_value' => 'decimal:3',
        'pack_count' => 'integer',
        'members_count' => 'integer',
        'brands_count' => 'integer',
    ];

    /**
     * Every member product (one per chain). The FK lives on products.
     */
    public function products(): HasMany
    {
        return $this->hasMany(Product::class);
    }

    /**
     * Latest offer per member product.
     *
     * Mirrors the latest-per-product logic in OfferController::index():
     * pick MAX(offers.id) per product_id over the canonical's members,
     * then re-query offers WHERE id IN (...). Returns an Eloquent
     * relation so callers can `->with(['currentOffers.product.brand'])`
     * for the comparison view in a single round trip.
     */
    public function currentOffers(): HasMany
    {
        $latestIds = Offer::query()
            ->selectRaw('MAX(offers.id) as id')
            ->join('products', 'products.id', '=', 'offers.product_id')
            ->where('products.canonical_product_id', $this->id)
            ->groupBy('offers.product_id');

        return $this->hasMany(Offer::class, 'product_id', 'id')
            ->setQuery(
                Offer::query()
                    ->with(['product.brand'])
                    ->whereIn('offers.id', $latestIds)
                    ->getQuery()
            );
    }

    /**
     * Recompute denormalised aggregates from current member state.
     *
     * Called at the end of a bulk-upsert batch — keeps the row's
     * `members_count`, `brands_count`, `image_url` and `display_name`
     * coherent with whatever the algorithm just wrote.
     *
     * Selection rules:
     *  - `image_url`: first member with a non-null image (deterministic
     *    via order by product id ascending — first crawled wins).
     *    Existing canonical image stays if no member has one.
     *  - `display_name`: keep the existing one unless it's empty — the
     *    algorithm owns the display name and writes it on upsert. We
     *    only fall back to a member's name if the canonical somehow has
     *    no display_name set (defensive).
     */
    public function refreshAggregates(): void
    {
        $counts = DB::table('products')
            ->where('canonical_product_id', $this->id)
            ->selectRaw('COUNT(*) as members_count, COUNT(DISTINCT brand_id) as brands_count')
            ->first();

        $this->members_count = (int) ($counts->members_count ?? 0);
        $this->brands_count = (int) ($counts->brands_count ?? 0);

        if ($this->image_url === null || $this->image_url === '') {
            $candidateImage = DB::table('products')
                ->where('canonical_product_id', $this->id)
                ->whereNotNull('image_url')
                ->where('image_url', '!=', '')
                ->orderBy('id')
                ->value('image_url');

            if ($candidateImage !== null) {
                $this->image_url = $candidateImage;
            }
        }

        if ($this->display_name === null || $this->display_name === '') {
            $candidateName = DB::table('products')
                ->where('canonical_product_id', $this->id)
                ->orderBy('id')
                ->value('name');

            if ($candidateName !== null) {
                $this->display_name = $candidateName;
            }
        }

        $this->save();
    }
}
