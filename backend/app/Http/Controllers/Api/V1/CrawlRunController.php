<?php

namespace App\Http\Controllers\Api\V1;

use App\Http\Controllers\Controller;
use App\Http\Requests\Api\V1\StartCrawlRunRequest;
use App\Http\Requests\Api\V1\UpdateCrawlRunRequest;
use App\Http\Resources\CrawlRunResource;
use App\Models\CrawlRun;
use Illuminate\Http\JsonResponse;
use Illuminate\Support\Carbon;

class CrawlRunController extends Controller
{
    /**
     * POST /api/v1/crawl-runs
     */
    public function store(StartCrawlRunRequest $request): JsonResponse
    {
        $data = $request->validated();

        $run = CrawlRun::create([
            'brand_id' => $data['brand_id'],
            'started_at' => Carbon::now(),
            'status' => CrawlRun::STATUS_RUNNING,
            'triggered_by' => $data['triggered_by'],
        ]);

        return (new CrawlRunResource($run))
            ->response()
            ->setStatusCode(201);
    }

    /**
     * PATCH /api/v1/crawl-runs/{run}
     */
    public function update(UpdateCrawlRunRequest $request, CrawlRun $run): CrawlRunResource
    {
        $data = $request->validated();

        $run->status = $data['status'];
        $run->offers_found = $data['offers_found'];

        if (array_key_exists('offers_persisted', $data) && $data['offers_persisted'] !== null) {
            $run->offers_persisted = $data['offers_persisted'];
        } else {
            // Auto-derive from the actual offers attached to the run.
            $run->offers_persisted = $run->offers()->count();
        }

        $run->error_message = $data['error_message'] ?? null;
        $run->finished_at = Carbon::now();
        $run->save();

        return new CrawlRunResource($run);
    }
}
