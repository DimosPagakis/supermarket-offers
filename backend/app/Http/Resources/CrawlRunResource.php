<?php

namespace App\Http\Resources;

use App\Models\CrawlRun;
use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\JsonResource;

/**
 * @mixin CrawlRun
 */
class CrawlRunResource extends JsonResource
{
    public function toArray(Request $request): array
    {
        return [
            'id' => $this->id,
            'brand_id' => (int) $this->brand_id,
            'status' => $this->status,
            'started_at' => $this->started_at?->toIso8601String(),
            'finished_at' => $this->finished_at?->toIso8601String(),
            'offers_found' => (int) $this->offers_found,
            'offers_persisted' => (int) $this->offers_persisted,
            'error_message' => $this->error_message,
            'triggered_by' => $this->triggered_by,
        ];
    }
}
