<?php

namespace App\Http\Controllers\Api\Public\V1;

use App\Http\Controllers\Controller;
use App\Http\Resources\Public\CategoryResource;
use App\Models\Product;
use Illuminate\Http\Resources\Json\AnonymousResourceCollection;
use Illuminate\Support\Facades\Cache;

class CategoryController extends Controller
{
    public const CACHE_KEY = 'public.v1.categories';

    public const CACHE_TTL_SECONDS = 3600;

    /**
     * GET /api/public/v1/categories
     *
     * Distinct, non-null `products.category` values for products that
     * belong to active brands. Cached for an hour — the set changes
     * once per crawl run at most.
     */
    public function index(): AnonymousResourceCollection
    {
        $categories = Cache::remember(self::CACHE_KEY, self::CACHE_TTL_SECONDS, function (): array {
            return Product::query()
                ->join('brands', 'brands.id', '=', 'products.brand_id')
                ->where('brands.active', true)
                ->whereNotNull('products.category')
                ->where('products.category', '!=', '')
                ->distinct()
                ->orderBy('products.category')
                ->pluck('products.category')
                ->all();
        });

        return CategoryResource::collection(collect($categories));
    }
}
