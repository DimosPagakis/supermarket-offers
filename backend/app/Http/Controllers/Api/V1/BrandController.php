<?php

namespace App\Http\Controllers\Api\V1;

use App\Http\Controllers\Controller;
use App\Http\Resources\BrandResource;
use App\Models\Brand;

class BrandController extends Controller
{
    /**
     * GET /api/v1/brands
     *
     * Returns active brands with their crawl_config so the crawler can
     * decide what to scrape and how.
     */
    public function index()
    {
        $brands = Brand::query()
            ->where('active', true)
            ->with('crawlConfig')
            ->orderBy('id')
            ->get();

        return BrandResource::collection($brands);
    }
}
