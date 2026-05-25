<?php

namespace App\Http\Controllers\Api\Public\V1;

use App\Http\Controllers\Controller;
use App\Http\Requests\Public\V1\FamilyIndexRequest;
use App\Http\Resources\Public\FamilyDetailResource;
use App\Http\Resources\Public\FamilySummaryResource;
use App\Models\Offer;
use App\Support\StringNormalizer;
use Illuminate\Database\Eloquent\Builder;
use Illuminate\Database\Query\Builder as QueryBuilder;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Resources\Json\ResourceCollection;
use Illuminate\Pagination\LengthAwarePaginator;
use Illuminate\Support\Carbon;
use Illuminate\Support\Facades\DB;

/**
 * Family-browse endpoints. A "family" is the deterministic tuple
 *   (manufacturer_brand, category_normalised, size_value, size_unit, pack_count)
 * derived at query time from the denormalised feature columns on
 * `products` (populated by {@see \App\Services\VariantDescriber}).
 *
 * This is intentionally NOT a canonicalisation reuse — see
 * `docs/canonicalisation-design.md` §"A note on family-browse" for the
 * design call. The Axe-150ml scent rejected from cross-chain
 * canonicalisation in Phase 2.1 IS a family here: shoppers want to
 * answer "which 150ml Axe deodorants are on offer right now,
 * irrespective of scent or chain".
 *
 * The list query groups directly off the composite
 * `products_family_idx`. The detail view returns the full member list
 * grouped by `variant_descriptor` so the UI can render an inline mini
 * price-comparison per scent / shade / flavour.
 */
class FamilyController extends Controller
{
    /**
     * GET /api/public/v1/families
     */
    public function index(FamilyIndexRequest $request): ResourceCollection
    {
        $filters = $request->validated();

        $minVariants = (int) ($filters['min_variants'] ?? 2);
        $minBrands = (int) ($filters['min_brands'] ?? 1);
        $sort = $filters['sort'] ?? 'variants_count';
        $dir = strtolower($filters['dir'] ?? 'desc');
        $perPage = (int) ($filters['per_page'] ?? 50);
        $page = (int) ($filters['page'] ?? 1);

        // Stage 1 — aggregate products into families (one row per
        // (manufacturer, category, size, unit, pack) tuple).
        $aggregates = DB::table('products')
            ->join('brands', 'brands.id', '=', 'products.brand_id')
            ->where('brands.active', true)
            ->whereNotNull('products.manufacturer_brand')
            ->whereNotNull('products.size_value')
            ->whereNotNull('products.size_unit')
            ->selectRaw('
                products.manufacturer_brand as manufacturer_brand,
                products.category_normalised as category_normalised,
                MAX(products.category) as category_display,
                products.size_value as size_value,
                products.size_unit as size_unit,
                products.pack_count as pack_count,
                COUNT(DISTINCT products.id) as variants_count,
                COUNT(DISTINCT products.brand_id) as brands_count
            ')
            ->groupBy(
                'products.manufacturer_brand',
                'products.category_normalised',
                'products.size_value',
                'products.size_unit',
                'products.pack_count',
            );

        $aggregates = $this->applyFamilyFilters($aggregates, $filters);

        // Subquery + outer query so we can filter on aggregates without
        // SQLite blowing up on HAVING + ORDER BY across complex
        // expressions. Outer scope owns the price join + ordering.
        $sub = $aggregates;

        $base = DB::query()
            ->fromSub($sub, 'fam')
            ->where('fam.variants_count', '>=', $minVariants)
            ->where('fam.brands_count', '>=', $minBrands);

        // Total — for pagination meta. SQLite-safe COUNT(*) over the
        // grouping subquery.
        $total = (int) DB::query()->fromSub($base, 'cnt')->count();

        // Price-aware ordering: prefetch pricing for the current page
        // when sort uses it; otherwise sort cheaply on the aggregate.
        $sortColumns = $this->resolveOrderColumns($sort, $dir);

        // For pure-aggregate sorts (variants_count / brands_count) we
        // can paginate at the DB layer and decorate only the page.
        // For price sorts we need to load all families and sort in PHP
        // since prices come from a second query — the catalogue is
        // ~12k products today and families collapse hard (< 5k rows),
        // so PHP-side sort is well within budget.
        $needsPriceSort = in_array($sort, ['min_price', 'avg_price'], true);

        if (! $needsPriceSort) {
            foreach ($sortColumns as [$col, $direction]) {
                $base->orderBy($col, $direction);
            }
            $rows = $base->offset(($page - 1) * $perPage)
                ->limit($perPage)
                ->get()
                ->all();

            $rows = $this->decorateWithPricing($rows);
        } else {
            // Fetch the whole family set, attach pricing, sort, then
            // paginate. Acceptable while the catalogue is in the
            // 4–8k families range; revisit when we hit 50k.
            $rows = $base->orderBy('fam.variants_count', 'desc')->get()->all();
            $rows = $this->decorateWithPricing($rows);
            usort($rows, function (array $a, array $b) use ($sort, $dir) {
                $av = $a[$sort] ?? null;
                $bv = $b[$sort] ?? null;
                if ($av === null && $bv === null) {
                    return 0;
                }
                if ($av === null) {
                    return 1; // nulls last regardless of dir
                }
                if ($bv === null) {
                    return -1;
                }
                $cmp = $av <=> $bv;

                return $dir === 'asc' ? $cmp : -$cmp;
            });
            $rows = array_slice($rows, ($page - 1) * $perPage, $perPage);
        }

        $paginator = new LengthAwarePaginator(
            items: $rows,
            total: $total,
            perPage: $perPage,
            currentPage: $page,
            options: [
                'path' => $request->url(),
                'pageName' => 'page',
            ],
        );
        $paginator->withQueryString();

        return FamilySummaryResource::collection($paginator);
    }

    /**
     * GET /api/public/v1/families/{key}
     *
     * `{key}` is the family's deterministic identifier — see
     * {@see self::familyKey()}. We URL-decode it, parse the four-part
     * shape, and pull every member product with their latest current
     * offers.
     *
     * 404 when the key is malformed or no products match — the family
     * doesn't exist (or doesn't have any active offers).
     */
    public function show(string $key): FamilyDetailResource|JsonResponse
    {
        $parts = $this->parseFamilyKey(rawurldecode($key));
        if ($parts === null) {
            return response()->json([
                'message' => 'Malformed family key.',
            ], 404);
        }
        [$manufacturer, $categoryNorm, $sizeValue, $sizeUnit, $pack] = $parts;

        $products = DB::table('products')
            ->join('brands', 'brands.id', '=', 'products.brand_id')
            ->where('brands.active', true)
            ->where('products.manufacturer_brand', $manufacturer)
            ->where('products.category_normalised', $categoryNorm)
            ->where('products.size_value', $sizeValue)
            ->where('products.size_unit', $sizeUnit)
            ->where('products.pack_count', $pack)
            ->select([
                'products.id', 'products.external_id', 'products.name',
                'products.url', 'products.image_url',
                'products.variant_descriptor', 'products.category',
                'products.manufacturer_brand', 'products.size_value',
                'products.size_unit', 'products.pack_count',
                'products.brand_id',
                'brands.id as b_id', 'brands.name as b_name', 'brands.slug as b_slug',
                'brands.country_code as b_country',
            ])
            ->orderBy('products.id')
            ->get();

        if ($products->isEmpty()) {
            return response()->json([
                'message' => 'Family not found.',
            ], 404);
        }

        // Latest current offer per product (mirrors the offers list
        // semantics elsewhere on the public API).
        $productIds = $products->pluck('id')->all();
        $latestOfferIds = Offer::query()
            ->whereIn('product_id', $productIds)
            ->select(DB::raw('MAX(id) as id'))
            ->groupBy('product_id')
            ->pluck('id');

        $offersByProduct = Offer::query()
            ->whereIn('id', $latestOfferIds)
            ->get()
            ->keyBy('product_id');

        // Restrict to currently-valid offers — NULL bounds are open.
        $today = Carbon::now()->toDateString();
        $offersByProduct = $offersByProduct->filter(function (Offer $o) use ($today): bool {
            $from = $o->valid_from?->toDateString();
            $to = $o->valid_to?->toDateString();

            return ($from === null || $from <= $today)
                && ($to === null || $to >= $today);
        });

        // Group members by variant_descriptor. NULL/empty descriptor
        // collapses to "—" so the UI has a stable bucket.
        $variantGroups = [];
        foreach ($products as $p) {
            $descriptor = $p->variant_descriptor !== null && $p->variant_descriptor !== ''
                ? $p->variant_descriptor
                : '—';
            $offer = $offersByProduct->get($p->id);
            $variantGroups[$descriptor] ??= [
                'variant_descriptor' => $descriptor,
                'products' => [],
                'prices' => [],
            ];
            $variantGroups[$descriptor]['products'][] = [
                'id' => (int) $p->id,
                'external_id' => $p->external_id,
                'name' => $p->name,
                'url' => $p->url,
                'image_url' => $p->image_url,
                'brand' => [
                    'id' => (int) $p->b_id,
                    'name' => $p->b_name,
                    'slug' => $p->b_slug,
                    'country_code' => $p->b_country,
                ],
                'offer' => $offer === null ? null : [
                    'id' => (int) $offer->id,
                    'price' => $offer->price !== null ? (float) $offer->price : null,
                    'original_price' => $offer->original_price !== null ? (float) $offer->original_price : null,
                    'discount_pct' => $offer->discount_pct !== null ? (int) $offer->discount_pct : null,
                    'promo_label' => $offer->promo_label,
                    'promo_type' => $offer->promo_type,
                    'valid_from' => $offer->valid_from?->format('Y-m-d'),
                    'valid_to' => $offer->valid_to?->format('Y-m-d'),
                    'scraped_at' => $offer->scraped_at?->toIso8601String(),
                ],
            ];
            if ($offer !== null && $offer->price !== null) {
                $variantGroups[$descriptor]['prices'][] = (float) $offer->price;
            }
        }

        // Per-variant aggregates + cheapest-brand pointer; sort
        // variants by minimum price (cheapest scent first).
        $variants = [];
        foreach ($variantGroups as $group) {
            // Order products inside the variant: cheapest first, then
            // unpriced rows fall to the bottom for stability.
            usort($group['products'], function (array $a, array $b): int {
                $pa = $a['offer']['price'] ?? null;
                $pb = $b['offer']['price'] ?? null;
                if ($pa === null && $pb === null) {
                    return 0;
                }
                if ($pa === null) {
                    return 1;
                }
                if ($pb === null) {
                    return -1;
                }

                return $pa <=> $pb;
            });

            $prices = $group['prices'];
            $cheapest = null;
            foreach ($group['products'] as $row) {
                if (($row['offer']['price'] ?? null) !== null) {
                    $cheapest = $row['brand'];
                    break;
                }
            }
            $variants[] = [
                'variant_descriptor' => $group['variant_descriptor'],
                'products' => $group['products'],
                'min_price' => $prices !== [] ? min($prices) : null,
                'max_price' => $prices !== [] ? max($prices) : null,
                'cheapest_brand' => $cheapest,
            ];
        }
        usort($variants, function (array $a, array $b): int {
            $pa = $a['min_price'] ?? null;
            $pb = $b['min_price'] ?? null;
            if ($pa === null && $pb === null) {
                return strcmp((string) $a['variant_descriptor'], (string) $b['variant_descriptor']);
            }
            if ($pa === null) {
                return 1;
            }
            if ($pb === null) {
                return -1;
            }

            return $pa <=> $pb;
        });

        $variantsCount = count($products);
        $brandsCount = $products->pluck('brand_id')->unique()->count();

        $allPrices = [];
        foreach ($offersByProduct as $offer) {
            if ($offer->price !== null) {
                $allPrices[] = (float) $offer->price;
            }
        }

        $first = $products->first();
        // Family image: first product image we can find (deterministic
        // — ordered by product id ascending above).
        $image = null;
        foreach ($products as $p) {
            if ($p->image_url !== null && $p->image_url !== '') {
                $image = $p->image_url;
                break;
            }
        }

        $detail = [
            'key' => $this->familyKey(
                (string) $first->manufacturer_brand,
                (string) $first->category,
                (float) $first->size_value,
                (string) $first->size_unit,
                (int) $first->pack_count,
            ),
            'manufacturer_brand' => $first->manufacturer_brand,
            'category' => $first->category,
            'category_normalised' => $categoryNorm,
            'size_value' => (float) $first->size_value,
            'size_unit' => $first->size_unit,
            'pack_count' => (int) $first->pack_count,
            'display_name' => $this->displayName(
                (string) $first->manufacturer_brand,
                $first->category,
                (float) $first->size_value,
                (string) $first->size_unit,
                (int) $first->pack_count,
            ),
            'image_url' => $image,
            'variants_count' => $variantsCount,
            'brands_count' => $brandsCount,
            'min_price' => $allPrices !== [] ? min($allPrices) : null,
            'max_price' => $allPrices !== [] ? max($allPrices) : null,
            'avg_price' => $allPrices !== [] ? array_sum($allPrices) / count($allPrices) : null,
            'variants' => $variants,
        ];

        return new FamilyDetailResource((object) $detail);
    }

    /**
     * Apply text + brand + manufacturer + category filters to the
     * aggregate query.
     *
     * @param QueryBuilder $query
     */
    private function applyFamilyFilters(QueryBuilder $query, array $filters): QueryBuilder
    {
        if (isset($filters['manufacturer']) && $filters['manufacturer'] !== '') {
            $query->where('products.manufacturer_brand', mb_strtolower((string) $filters['manufacturer'], 'UTF-8'));
        }

        if (isset($filters['category']) && $filters['category'] !== '') {
            $query->where('products.category_normalised', StringNormalizer::normalize((string) $filters['category']));
        }

        if (isset($filters['brand']) && $filters['brand'] !== '') {
            $slugs = array_values(array_filter(array_map('trim', explode(',', (string) $filters['brand']))));
            if ($slugs !== []) {
                // "Families with at least one member in any of these
                // brand slugs." Use a correlated EXISTS so the brand
                // filter doesn't reduce the inner row set (and thus
                // the variants_count aggregate) — the family stays
                // sized by ALL its members, we just gate visibility
                // on whether one of those members is in the slug set.
                $query->whereExists(function ($q) use ($slugs): void {
                    $q->select(DB::raw(1))
                        ->from('products as pf')
                        ->join('brands as bf', 'bf.id', '=', 'pf.brand_id')
                        ->whereColumn('pf.manufacturer_brand', 'products.manufacturer_brand')
                        ->whereColumn('pf.category_normalised', 'products.category_normalised')
                        ->whereColumn('pf.size_value', 'products.size_value')
                        ->whereColumn('pf.size_unit', 'products.size_unit')
                        ->whereColumn('pf.pack_count', 'products.pack_count')
                        ->where('bf.active', true)
                        ->whereIn('bf.slug', $slugs);
                });
            }
        }

        if (isset($filters['q']) && $filters['q'] !== '') {
            // `q` is a text search on the family display name. Since
            // the display name is derived from manufacturer + category
            // + size, normalising the needle and OR-ing across the
            // underlying columns gives a stable answer.
            $needle = StringNormalizer::normalize((string) $filters['q']);
            $query->where(function ($q) use ($needle): void {
                $q->where('products.manufacturer_brand', 'like', '%'.$needle.'%')
                    ->orWhere('products.category_normalised', 'like', '%'.$needle.'%')
                    ->orWhere('products.normalized_name', 'like', '%'.$needle.'%');
            });
        }

        return $query;
    }

    /**
     * @return array<int, array{0: string, 1: string}>
     */
    private function resolveOrderColumns(string $sort, string $dir): array
    {
        $dir = $dir === 'asc' ? 'asc' : 'desc';

        return match ($sort) {
            'brands_count' => [
                ['fam.brands_count', $dir],
                ['fam.variants_count', 'desc'],
            ],
            'variants_count' => [
                ['fam.variants_count', $dir],
                ['fam.brands_count', 'desc'],
            ],
            default => [
                ['fam.variants_count', 'desc'],
                ['fam.brands_count', 'desc'],
            ],
        };
    }

    /**
     * Compute min/avg/max + cheapest brand for each family page row.
     * One pass: load every product matching the page's families, pull
     * the latest offer per product, fold into per-family stats.
     *
     * @param array<int, object> $rows
     * @return array<int, array<string, mixed>>
     */
    private function decorateWithPricing(array $rows): array
    {
        if ($rows === []) {
            return [];
        }

        // Build the disjunction of family tuples for the IN clause.
        // SQLite doesn't support row-value IN, so we OR groups.
        $productsQuery = DB::table('products')
            ->join('brands', 'brands.id', '=', 'products.brand_id')
            ->where('brands.active', true)
            ->where(function ($q) use ($rows): void {
                foreach ($rows as $row) {
                    $q->orWhere(function ($qq) use ($row): void {
                        $qq->where('products.manufacturer_brand', $row->manufacturer_brand)
                            ->where('products.category_normalised', $row->category_normalised)
                            ->where('products.size_value', $row->size_value)
                            ->where('products.size_unit', $row->size_unit)
                            ->where('products.pack_count', $row->pack_count);
                    });
                }
            })
            ->select([
                'products.id', 'products.image_url',
                'products.manufacturer_brand', 'products.category_normalised',
                'products.size_value', 'products.size_unit', 'products.pack_count',
                'brands.id as b_id', 'brands.name as b_name', 'brands.slug as b_slug',
            ])
            ->get();

        $productsByFamily = [];
        foreach ($productsQuery as $p) {
            $k = $this->familyTupleKey(
                $p->manufacturer_brand,
                $p->category_normalised,
                (float) $p->size_value,
                $p->size_unit,
                (int) $p->pack_count,
            );
            $productsByFamily[$k] ??= [];
            $productsByFamily[$k][] = $p;
        }

        $productIds = $productsQuery->pluck('id')->all();
        $latestOfferIds = Offer::query()
            ->whereIn('product_id', $productIds)
            ->select(DB::raw('MAX(id) as id'))
            ->groupBy('product_id')
            ->pluck('id');

        $offersByProduct = Offer::query()
            ->whereIn('id', $latestOfferIds)
            ->get()
            ->keyBy('product_id');

        $today = Carbon::now()->toDateString();

        $out = [];
        foreach ($rows as $row) {
            $k = $this->familyTupleKey(
                $row->manufacturer_brand,
                $row->category_normalised,
                (float) $row->size_value,
                $row->size_unit,
                (int) $row->pack_count,
            );
            $members = $productsByFamily[$k] ?? [];

            $prices = [];
            $cheapestBrand = null;
            $cheapestPrice = null;
            $image = null;
            foreach ($members as $member) {
                if ($image === null && $member->image_url !== null && $member->image_url !== '') {
                    $image = $member->image_url;
                }
                $offer = $offersByProduct->get($member->id);
                if ($offer === null || $offer->price === null) {
                    continue;
                }
                $from = $offer->valid_from?->toDateString();
                $to = $offer->valid_to?->toDateString();
                $valid = ($from === null || $from <= $today)
                    && ($to === null || $to >= $today);
                if (! $valid) {
                    continue;
                }
                $price = (float) $offer->price;
                $prices[] = $price;
                if ($cheapestPrice === null || $price < $cheapestPrice) {
                    $cheapestPrice = $price;
                    $cheapestBrand = [
                        'id' => (int) $member->b_id,
                        'name' => $member->b_name,
                        'slug' => $member->b_slug,
                    ];
                }
            }

            $out[] = [
                'key' => $this->familyKey(
                    (string) $row->manufacturer_brand,
                    (string) ($row->category_display ?? ''),
                    (float) $row->size_value,
                    (string) $row->size_unit,
                    (int) $row->pack_count,
                ),
                'manufacturer_brand' => $row->manufacturer_brand,
                'category' => $row->category_display ?? null,
                'category_normalised' => $row->category_normalised,
                'size_value' => (float) $row->size_value,
                'size_unit' => $row->size_unit,
                'pack_count' => (int) $row->pack_count,
                'display_name' => $this->displayName(
                    (string) $row->manufacturer_brand,
                    $row->category_display ?? null,
                    (float) $row->size_value,
                    (string) $row->size_unit,
                    (int) $row->pack_count,
                ),
                'image_url' => $image,
                'variants_count' => (int) $row->variants_count,
                'brands_count' => (int) $row->brands_count,
                'min_price' => $prices !== [] ? min($prices) : null,
                'max_price' => $prices !== [] ? max($prices) : null,
                'avg_price' => $prices !== [] ? array_sum($prices) / count($prices) : null,
                'cheapest_brand' => $cheapestBrand,
            ];
        }

        return $out;
    }

    /**
     * Deterministic, URL-safe family key. Uses `|` as the separator
     * because the constituent fields can contain spaces and forward
     * slashes; `|` doesn't appear in any of our category names.
     *
     * Shape: `<manufacturer>|<category_normalised>|<size_value>|<size_unit>|<pack>`
     *
     * The category is folded via {@see StringNormalizer::normalize()}
     * to match the indexed column.
     */
    public function familyKey(
        string $manufacturer,
        string $category,
        float $sizeValue,
        string $sizeUnit,
        int $pack,
    ): string {
        $categoryNorm = StringNormalizer::normalize($category);
        $sizeStr = $this->formatSize($sizeValue);

        return $manufacturer.'|'.$categoryNorm.'|'.$sizeStr.'|'.$sizeUnit.'|'.$pack;
    }

    /**
     * Hash for the pricing decorator's by-family bucket. Uses the
     * pre-normalised category so it matches the DB row's
     * `category_normalised` exactly.
     */
    private function familyTupleKey(
        string $manufacturer,
        ?string $categoryNorm,
        float $sizeValue,
        string $sizeUnit,
        int $pack,
    ): string {
        return $manufacturer.'|'.($categoryNorm ?? '').'|'
            .$this->formatSize($sizeValue).'|'.$sizeUnit.'|'.$pack;
    }

    /**
     * @return array{0: string, 1: string, 2: float, 3: string, 4: int}|null
     */
    private function parseFamilyKey(string $key): ?array
    {
        $parts = explode('|', $key);
        if (count($parts) !== 5) {
            return null;
        }
        [$manufacturer, $categoryNorm, $sizeRaw, $sizeUnit, $packRaw] = $parts;
        if ($manufacturer === '' || $categoryNorm === '' || $sizeRaw === '' || $sizeUnit === '') {
            return null;
        }
        if (! is_numeric($sizeRaw) || ! is_numeric($packRaw)) {
            return null;
        }

        return [$manufacturer, $categoryNorm, (float) $sizeRaw, $sizeUnit, (int) $packRaw];
    }

    /**
     * Render a human display name from the family tuple. Title-cases
     * the manufacturer (which we store in lowercase) so the card heading
     * reads naturally: "Axe Αποσμητικά σώματος 150ml".
     */
    public function displayName(
        string $manufacturer,
        ?string $category,
        float $sizeValue,
        string $sizeUnit,
        int $pack,
    ): string {
        $brand = ucwords(str_replace('-', ' ', $manufacturer));
        $size = $this->formatSize($sizeValue).$sizeUnit;
        $packed = $pack > 1 ? $pack.'×'.$size : $size;
        $parts = [$brand];
        if ($category !== null && $category !== '') {
            $parts[] = $category;
        }
        $parts[] = $packed;

        return implode(' ', $parts);
    }

    private function formatSize(float $value): string
    {
        if (floor($value) === $value) {
            return (string) (int) $value;
        }

        return rtrim(rtrim(number_format($value, 3, '.', ''), '0'), '.');
    }
}
