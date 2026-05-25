<?php

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
