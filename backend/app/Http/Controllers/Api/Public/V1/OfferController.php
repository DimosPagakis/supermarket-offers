<?php

namespace App\Http\Controllers\Api\Public\V1;

use App\Http\Controllers\Controller;
use App\Http\Requests\Public\V1\OfferIndexRequest;
use App\Http\Requests\Public\V1\OfferShowRequest;
use App\Http\Resources\Public\OfferResource;
use App\Models\Brand;
use App\Models\Offer;
use App\Support\StringNormalizer;
use Illuminate\Database\Eloquent\Builder;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Resources\Json\ResourceCollection;
use Illuminate\Support\Carbon;

class OfferController extends Controller
{
    /**
     * GET /api/public/v1/offers
     *
     * Default behaviour:
     *  - Returns one offer per product — the latest by scraped_at among the
     *    rows that matched every active filter. We pick the latest with a
     *    correlated subquery (MAX(id) GROUP BY product_id over the filtered
     *    set) rather than a window function so the path works identically
     *    on SQLite and Postgres without raw SQL.
     *  - `valid_on` defaults to today (server timezone). NULL bounds in
     *    `valid_from` / `valid_to` are treated as open (always valid).
     *  - `q` searches against `products.normalized_name` using the same
     *    Greek-accent-stripping normaliser the crawler ingest path uses,
     *    so "feta" matches "Φέτα ΠΟΠ".
     *
     * Sort order is applied after the latest-per-product collapse. Default
     * `sort=discount_pct&dir=desc` is the most useful for an offers feed.
     */
    public function index(OfferIndexRequest $request, ?Brand $brand = null): ResourceCollection
    {
        $filters = $request->validated();

        // The route can pin to one brand (/brands/{slug}/offers) or the
        // query string can scope to a CSV of slugs (?brand=ab,lidl).
        // Route binding wins when present.
        $brandSlugs = match (true) {
            $brand !== null => [$brand->slug],
            isset($filters['brand']) => $this->parseCsv((string) $filters['brand']),
            default => null,
        };

        $base = $this->buildFilteredOfferQuery($filters, $brandSlugs);

        // Collapse to one offer per product (latest by id). See
        // Offer::latestPerProductIds() for the why-MAX(id) rationale.
        $latestIds = Offer::latestPerProductIds($base);

        $sort = $filters['sort'] ?? 'discount_pct';
        $dir = $filters['dir'] ?? 'desc';
        $perPage = (int) ($filters['per_page'] ?? 50);
        $page = (int) ($filters['page'] ?? 1);

        // discount_pct can be NULL; sort NULLs last on a desc, first on asc
        // by coercing them to a sentinel via COALESCE so pagination stays
        // deterministic across pages.
        $sortExpr = match ($sort) {
            'price' => 'offers.price',
            'scraped_at' => 'offers.scraped_at',
            default => 'COALESCE(offers.discount_pct, 0)',
        };

        $query = Offer::query()
            ->with(['product.brand'])
            ->whereIn('offers.id', $latestIds)
            ->orderByRaw("{$sortExpr} {$dir}")
            ->orderBy('offers.id', 'desc'); // tiebreaker for deterministic pagination

        $paginator = $query->paginate(perPage: $perPage, page: $page);
        $paginator->withQueryString();

        // OfferResource::collection() returns a custom collection class
        // that adds a `self` link to the framework's standard
        // first/last/prev/next block — see OfferResourceCollection.
        return OfferResource::collection($paginator);
    }

    /**
     * GET /api/public/v1/offers/{id}
     *
     * ?include_history=true attaches the price history for the offer's
     * product, ordered newest first, capped at 200 entries. The cap keeps
     * a misbehaving client from forcing the backend to ship megabytes for
     * a product crawled hourly for a year.
     */
    public function show(OfferShowRequest $request, Offer $offer): OfferResource
    {
        $offer->load(['product.brand']);

        if ($request->boolean('include_history')) {
            $history = Offer::query()
                ->where('product_id', $offer->product_id)
                ->orderByDesc('scraped_at')
                ->orderByDesc('id')
                ->limit(200)
                ->get(['id', 'price', 'original_price', 'discount_pct', 'promo_label', 'promo_type', 'currency', 'scraped_at'])
                ->map(fn (Offer $row) => [
                    'id' => (int) $row->id,
                    'price' => $row->price !== null ? (float) $row->price : null,
                    'original_price' => $row->original_price !== null ? (float) $row->original_price : null,
                    'discount_pct' => $row->discount_pct !== null ? (int) $row->discount_pct : null,
                    'promo_label' => $row->promo_label,
                    'promo_type' => $row->promo_type,
                    'currency' => $row->currency,
                    'scraped_at' => $row->scraped_at?->toIso8601String(),
                ])
                ->all();

            // Stash on the model so OfferResource can surface it.
            $offer->additional_history = $history;
        }

        return new OfferResource($offer);
    }

    /**
     * Build the filtered offer query that the latest-per-product subquery
     * is computed against. Used by both /offers and the brand-scoped sugar.
     */
    private function buildFilteredOfferQuery(array $filters, ?array $brandSlugs): Builder
    {
        $query = Offer::query()
            ->from('offers')
            ->join('products', 'products.id', '=', 'offers.product_id')
            ->join('brands', 'brands.id', '=', 'products.brand_id')
            ->where('brands.active', true);

        if ($brandSlugs !== null && $brandSlugs !== []) {
            $query->whereIn('brands.slug', $brandSlugs);
        }

        if (isset($filters['category']) && $filters['category'] !== '') {
            // Case-insensitive exact match across Greek casing variants —
            // SQLite's LOWER() is ASCII-only so we enumerate explicitly.
            $query->whereIn('products.category', StringNormalizer::caseVariants($filters['category']));
        }

        if (isset($filters['min_discount'])) {
            $query->where('offers.discount_pct', '>=', (int) $filters['min_discount']);
        }

        if (array_key_exists('has_discount', $filters) && filter_var($filters['has_discount'], FILTER_VALIDATE_BOOLEAN)) {
            $query->whereNotNull('offers.original_price')
                ->whereColumn('offers.original_price', '>', 'offers.price');
        }

        // valid_on: NULL bounds are open. Default to today.
        //
        // SQLite stores `date` columns as `YYYY-MM-DD 00:00:00` strings,
        // so comparing against a bare `YYYY-MM-DD` literal puts the
        // stored value strictly greater (the trailing space character
        // sorts after end-of-string). Compare against an end-of-day cap
        // for valid_from and a start-of-day floor for valid_to so the
        // window check works on both SQLite and Postgres.
        $validOn = $filters['valid_on'] ?? Carbon::now()->toDateString();
        $endOfDay = $validOn.' 23:59:59';
        $startOfDay = $validOn.' 00:00:00';
        $query->where(function (Builder $q) use ($endOfDay): void {
            $q->whereNull('offers.valid_from')->orWhere('offers.valid_from', '<=', $endOfDay);
        })->where(function (Builder $q) use ($startOfDay): void {
            $q->whereNull('offers.valid_to')->orWhere('offers.valid_to', '>=', $startOfDay);
        });

        if (isset($filters['q']) && $filters['q'] !== '') {
            $normalized = StringNormalizer::normalize($filters['q']);
            $query->where('products.normalized_name', 'like', '%'.$normalized.'%');
        }

        return $query->select('offers.*');
    }

    /**
     * Parse a CSV query parameter into a clean list — trimmed, with
     * empty entries dropped. Returns a 0-indexed array suitable for
     * `whereIn`. An all-empty input collapses to an empty array which
     * the caller should treat as "no filter".
     *
     * @return array<int, string>
     */
    private function parseCsv(string $value): array
    {
        return array_values(array_filter(array_map('trim', explode(',', $value)), fn (string $s) => $s !== ''));
    }

    /**
     * GET /api/public/v1/search?q=...
     *
     * Convenience alias of /offers?q=... so third-party clients building
     * search-first UIs have a memorable endpoint. All other query
     * parameters from /offers are honoured.
     */
    public function search(OfferIndexRequest $request): ResourceCollection|JsonResponse
    {
        if (! $request->filled('q')) {
            return response()->json([
                'message' => "The 'q' query parameter is required for /search.",
                'errors' => ['q' => ["The 'q' query parameter is required for /search."]],
            ], 422);
        }

        return $this->index($request);
    }
}
