<?php

namespace App\Http\Controllers\Api\Public\V1;

use App\Http\Controllers\Controller;
use App\Http\Requests\Public\V1\CanonicalProductIndexRequest;
use App\Http\Resources\Public\CanonicalProductDetailResource;
use App\Http\Resources\Public\CanonicalProductListResource;
use App\Models\CanonicalProduct;
use App\Models\Offer;
use Illuminate\Http\Resources\Json\ResourceCollection;
use Illuminate\Support\Carbon;
use Illuminate\Support\Facades\DB;

class CanonicalProductController extends Controller
{
    /**
     * GET /api/public/v1/canonical-products
     *
     * Defaults: only canonicals with brands_count >= 2 (so the
     * comparison list is comparison-meaningful by default); sort
     * brands_count desc with members_count as a stable tiebreaker.
     *
     * The list view enriches each canonical with min/max/avg current
     * prices and the cheapest brand. We compute those in a single
     * follow-up query against the latest offer per member product —
     * the same MAX(offers.id) GROUP BY product_id technique used by
     * the offers list endpoint — so the response is shippable to the
     * frontend without a second round trip.
     */
    public function index(CanonicalProductIndexRequest $request): ResourceCollection
    {
        $filters = $request->validated();

        $minBrands = (int) ($filters['min_brands'] ?? 2);
        $sort = $filters['sort'] ?? 'brands_count';
        $dir = $filters['dir'] ?? 'desc';
        $perPage = (int) ($filters['per_page'] ?? 50);
        $page = (int) ($filters['page'] ?? 1);

        $query = CanonicalProduct::query()
            ->where('brands_count', '>=', $minBrands);

        if (isset($filters['q']) && $filters['q'] !== '') {
            // The list `q` filter is intentionally simpler than the
            // offers `q` filter — canonical display names are curated
            // by the algorithm so accent-stripping isn't worth the
            // extra column. Plain case-insensitive LIKE is enough.
            $needle = '%'.$filters['q'].'%';
            $query->where('display_name', 'like', $needle);
        }

        if (isset($filters['category']) && $filters['category'] !== '') {
            // Same case-insensitive variant trick as the offers
            // endpoint — SQLite's LOWER() is ASCII-only.
            $category = $filters['category'];
            $variants = array_values(array_unique([
                $category,
                mb_strtolower($category, 'UTF-8'),
                mb_strtoupper($category, 'UTF-8'),
                mb_convert_case($category, MB_CASE_TITLE, 'UTF-8'),
            ]));
            $query->whereIn('category', $variants);
        }

        if (isset($filters['brand']) && $filters['brand'] !== '') {
            $brandSlugs = array_values(array_filter(array_map(
                'trim',
                explode(',', (string) $filters['brand']),
            )));

            if ($brandSlugs !== []) {
                // "Canonicals with at least one member in any of these
                // brand slugs." Subquery keeps the outer pagination
                // simple and matches the per_page semantics.
                $query->whereExists(function ($q) use ($brandSlugs): void {
                    $q->select(DB::raw(1))
                        ->from('products')
                        ->join('brands', 'brands.id', '=', 'products.brand_id')
                        ->whereColumn('products.canonical_product_id', 'canonical_products.id')
                        ->whereIn('brands.slug', $brandSlugs);
                });
            }
        }

        // members_count is a useful tiebreaker for the default sort
        // (more chains > equal chains, more members); display_name asc
        // gives a stable secondary order for the textual sort.
        $sortMap = [
            'brands_count' => ['brands_count', 'members_count'],
            'members_count' => ['members_count', 'brands_count'],
            'display_name' => ['display_name'],
        ];
        foreach ($sortMap[$sort] as $col) {
            $query->orderBy($col, $dir);
        }
        $query->orderBy('id', 'asc'); // final deterministic tiebreaker

        $paginator = $query->paginate(perPage: $perPage, page: $page);
        $paginator->withQueryString();

        $this->decorateWithPricing($paginator->getCollection());

        return CanonicalProductListResource::collection($paginator);
    }

    /**
     * GET /api/public/v1/canonical-products/{id}
     *
     * Returns the comparison view: one current offer per member
     * product, ordered cheapest first. Latest-per-product semantics
     * match the offers list endpoint.
     */
    public function show(CanonicalProduct $canonicalProduct): CanonicalProductDetailResource
    {
        // Fetch latest offer per member product. Same correlated-MAX
        // technique used elsewhere — portable across SQLite and Postgres.
        $latestIds = Offer::query()
            ->selectRaw('MAX(offers.id) as id')
            ->join('products', 'products.id', '=', 'offers.product_id')
            ->where('products.canonical_product_id', $canonicalProduct->id)
            ->groupBy('offers.product_id');

        $offers = Offer::query()
            ->with(['product.brand'])
            ->whereIn('offers.id', $latestIds)
            ->get();

        // Restrict to currently-valid offers — NULL bounds are open.
        $today = Carbon::now()->toDateString();
        $offers = $offers->filter(function (Offer $o) use ($today): bool {
            $from = $o->valid_from?->toDateString();
            $to = $o->valid_to?->toDateString();

            return ($from === null || $from <= $today)
                && ($to === null || $to >= $today);
        });

        $shaped = $offers
            ->map(function (Offer $o): array {
                return [
                    'brand' => [
                        'id' => (int) $o->product->brand->id,
                        'name' => $o->product->brand->name,
                        'slug' => $o->product->brand->slug,
                        'country_code' => $o->product->brand->country_code,
                    ],
                    'product' => [
                        'id' => (int) $o->product->id,
                        'name' => $o->product->name,
                        'url' => $o->product->url,
                        'image_url' => $o->product->image_url,
                    ],
                    'offer' => [
                        'id' => (int) $o->id,
                        'price' => $o->price !== null ? (float) $o->price : null,
                        'original_price' => $o->original_price !== null ? (float) $o->original_price : null,
                        'discount_pct' => $o->discount_pct !== null ? (int) $o->discount_pct : null,
                        'valid_from' => optional($o->valid_from)->format('Y-m-d'),
                        'valid_to' => optional($o->valid_to)->format('Y-m-d'),
                        'scraped_at' => optional($o->scraped_at)->toIso8601String(),
                    ],
                ];
            })
            ->sortBy(fn (array $row) => $row['offer']['price'] ?? PHP_FLOAT_MAX)
            ->values()
            ->all();

        $prices = array_filter(array_map(fn (array $row) => $row['offer']['price'], $shaped), fn ($p) => $p !== null);

        $canonicalProduct->comparison_offers = $shaped;
        $canonicalProduct->min_price = $prices !== [] ? min($prices) : null;
        $canonicalProduct->max_price = $prices !== [] ? max($prices) : null;
        $canonicalProduct->avg_price = $prices !== [] ? array_sum($prices) / count($prices) : null;
        $canonicalProduct->price_savings = $prices !== []
            ? ($canonicalProduct->max_price - $canonicalProduct->min_price)
            : null;

        return new CanonicalProductDetailResource($canonicalProduct);
    }

    /**
     * Compute min/max/avg current prices and cheapest brand for each
     * canonical in the supplied page, in one pass.
     *
     * "Current" mirrors the latest-per-product semantics elsewhere on
     * the public API (MAX(offers.id) GROUP BY product_id over the
     * canonical's members) without the valid_on window — the list
     * view is more forgiving than the detail view so an offer that
     * expired yesterday still surfaces a comparison row.
     *
     * @param  iterable<int, CanonicalProduct>  $canonicals
     */
    private function decorateWithPricing(iterable $canonicals): void
    {
        $ids = collect($canonicals)->pluck('id')->all();
        if ($ids === []) {
            return;
        }

        $latestIds = Offer::query()
            ->selectRaw('MAX(offers.id) as id')
            ->join('products', 'products.id', '=', 'offers.product_id')
            ->whereIn('products.canonical_product_id', $ids)
            ->groupBy('offers.product_id');

        $rows = Offer::query()
            ->with(['product.brand'])
            ->whereIn('offers.id', $latestIds)
            ->get();

        $byCanonical = [];
        foreach ($rows as $offer) {
            $cid = (int) $offer->product->canonical_product_id;
            $byCanonical[$cid] ??= [];
            $byCanonical[$cid][] = $offer;
        }

        foreach ($canonicals as $canonical) {
            $offers = $byCanonical[$canonical->id] ?? [];
            $prices = array_values(array_filter(array_map(
                fn (Offer $o) => $o->price !== null ? (float) $o->price : null,
                $offers,
            ), fn ($p) => $p !== null));

            if ($prices === []) {
                $canonical->min_price = null;
                $canonical->max_price = null;
                $canonical->avg_price = null;
                $canonical->cheapest_brand = null;

                continue;
            }

            $canonical->min_price = min($prices);
            $canonical->max_price = max($prices);
            $canonical->avg_price = array_sum($prices) / count($prices);

            // Cheapest brand: pick the offer with the lowest price; ties
            // are broken by the latest (highest) offer id for stability.
            $cheapest = null;
            foreach ($offers as $o) {
                if ($o->price === null) {
                    continue;
                }
                if ($cheapest === null
                    || (float) $o->price < (float) $cheapest->price
                    || ((float) $o->price === (float) $cheapest->price && $o->id > $cheapest->id)
                ) {
                    $cheapest = $o;
                }
            }

            if ($cheapest !== null && $cheapest->product?->brand) {
                $canonical->cheapest_brand = [
                    'id' => (int) $cheapest->product->brand->id,
                    'name' => $cheapest->product->brand->name,
                    'slug' => $cheapest->product->brand->slug,
                ];
            } else {
                $canonical->cheapest_brand = null;
            }
        }
    }
}
