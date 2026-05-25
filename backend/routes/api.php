<?php

use App\Http\Controllers\Api\Public\V1\BrandController as PublicBrandController;
use App\Http\Controllers\Api\Public\V1\CategoryController as PublicCategoryController;
use App\Http\Controllers\Api\Public\V1\OfferController as PublicOfferController;
use App\Http\Controllers\Api\V1\BrandController;
use App\Http\Controllers\Api\V1\CrawlRunController;
use App\Http\Controllers\Api\V1\CrawlRunOfferController;
use Illuminate\Support\Facades\Route;

Route::prefix('v1')
    ->middleware(['auth:sanctum', 'ability:crawler:write'])
    ->group(function (): void {
        Route::get('/brands', [BrandController::class, 'index']);

        Route::post('/crawl-runs', [CrawlRunController::class, 'store']);
        Route::patch('/crawl-runs/{run}', [CrawlRunController::class, 'update']);
        Route::post('/crawl-runs/{run}/offers', [CrawlRunOfferController::class, 'store']);
    });

/*
|--------------------------------------------------------------------------
| Public read API — /api/public/v1/*
|--------------------------------------------------------------------------
|
| No auth. Throttled by IP at 120 req/min. CORS is enabled for all origins
| via config/cors.php — the frontend (Next.js on a different local port)
| and third-party consumers both hit this surface.
|
| The /v1 prefix is the stability contract: we ship /v2 before we ever
| break this. See backend/docs/public-api.md.
*/
Route::prefix('public/v1')
    ->middleware('throttle:120,1')
    ->group(function (): void {
        Route::get('/brands', [PublicBrandController::class, 'index']);
        Route::get('/categories', [PublicCategoryController::class, 'index']);

        Route::get('/offers', [PublicOfferController::class, 'index']);
        Route::get('/offers/{offer}', [PublicOfferController::class, 'show']);

        // Brand-scoped sugar: /brands/{slug}/offers behaves like
        // /offers?brand={slug} but accepts the slug positionally.
        Route::get('/brands/{brand:slug}/offers', [PublicOfferController::class, 'index'])
            ->scopeBindings();

        Route::get('/search', [PublicOfferController::class, 'search']);
    });
