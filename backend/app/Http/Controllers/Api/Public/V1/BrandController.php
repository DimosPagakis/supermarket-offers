<?php

namespace App\Http\Controllers\Api\Public\V1;

use App\Http\Controllers\Controller;
use App\Http\Resources\Public\BrandResource;
use App\Models\Brand;
use Illuminate\Http\Resources\Json\AnonymousResourceCollection;

class BrandController extends Controller
{
    /**
     * GET /api/public/v1/brands
     *
     * Lists active brands. No crawl config — that's an internal detail
     * the public surface doesn't expose. Five rows; no pagination.
     */
    public function index(): AnonymousResourceCollection
    {
        $brands = Brand::query()
            ->where('active', true)
            ->orderBy('name')
            ->get();

        return BrandResource::collection($brands);
    }
}
